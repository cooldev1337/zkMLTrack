// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "openzeppelin-contracts/contracts/access/Ownable.sol";
import "openzeppelin-contracts/contracts/utils/cryptography/MerkleProof.sol";

/**
 * @title MainControllerPrototype
 * @notice Prototype for tracking model accuracy through on-chain incremental verification
 * @dev Each task has its own dataset Merkle root and set of model evaluations.
 */
contract MainControllerPrototype is Ownable {

    // ========= Structures =========

    struct Task {
        bytes32 datasetMerkleRoot;
        address bestVerifier;
        uint256 bestAccuracy; // basis points (9500 = 95%)
        bool exists;
    }

    struct EvaluationProgress {
        uint256 totalSamples;
        uint256 correctSamples;
        bool finalized;
    }

    // ========= State =========

    // taskId → Task metadata
    mapping(uint256 => Task) public tasks;

    // taskId → verifier → EvaluationProgress
    mapping(uint256 => mapping(address => EvaluationProgress)) public evaluations;

    // taskId → verifier → registered flag
    mapping(uint256 => mapping(address => bool)) public verifierRegistered;

    // ========= Events =========

    event TaskCreated(uint256 indexed taskId, bytes32 merkleRoot, address indexed creator);
    event SampleVerified(uint256 indexed taskId, address indexed verifier, bool correct, uint256 totalVerified);
    event EvaluationFinalized(uint256 indexed taskId, address indexed verifier, uint256 accuracy);
    event BestVerifierUpdated(uint256 indexed taskId, address indexed verifier, uint256 newAccuracy);

    // ========= Functions =========

    /**
     * @notice Create a new task with its dataset Merkle root
     * @param taskId Unique ID for the task
     * @param merkleRoot Merkle root of the validation dataset
     */
    function createTask(uint256 taskId, bytes32 merkleRoot) external {
        require(!tasks[taskId].exists, "Task already exists");
        require(merkleRoot != bytes32(0), "Invalid merkle root");

        tasks[taskId] = Task({
            datasetMerkleRoot: merkleRoot,
            bestVerifier: address(0),
            bestAccuracy: 0,
            exists: true
        });

        emit TaskCreated(taskId, merkleRoot, msg.sender);
    }

    /**
     * @notice Submit a single proof result for a model’s evaluation
     * @dev This is called one by one for each sample
     * @param taskId ID of the task
     * @param verifier Address of the model verifier contract
     * @param leaf Hash of the validation sample
     * @param proof Merkle proof of inclusion
     * @param correct Whether model prediction was correct for this sample
     * @param totalToVerify Total number of samples expected for this evaluation (e.g. 20)
     */
    function submitSampleProof(
        uint256 taskId,
        address verifier,
        bytes32 leaf,
        bytes32[] calldata proof,
        bool correct,
        uint256 totalToVerify
    ) external {
        Task storage t = tasks[taskId];
        require(t.exists, "Task does not exist");

        EvaluationProgress storage ev = evaluations[taskId][verifier];
        require(!ev.finalized, "Evaluation already finalized");

        // Verify inclusion proof in dataset
        bool valid = MerkleProof.verify(proof, t.datasetMerkleRoot, leaf);
        require(valid, "Invalid Merkle proof");

        // Increment counters
        ev.totalSamples += 1;
        if (correct) ev.correctSamples += 1;

        emit SampleVerified(taskId, verifier, correct, ev.totalSamples);

        // Check if evaluation completed
        if (ev.totalSamples == totalToVerify) {
            ev.finalized = true;

            // Compute accuracy (basis points)
            uint256 accuracy = (ev.correctSamples * 10000) / totalToVerify;

            // If better than current best, update
            if (accuracy > t.bestAccuracy) {
                t.bestVerifier = verifier;
                t.bestAccuracy = accuracy;
                emit BestVerifierUpdated(taskId, verifier, accuracy);
            }

            emit EvaluationFinalized(taskId, verifier, accuracy);
        }
    }

    /**
     * @notice Get task's best model info
     */
    function getBestVerifier(uint256 taskId) external view returns (address, uint256) {
        Task memory t = tasks[taskId];
        return (t.bestVerifier, t.bestAccuracy);
    }
}