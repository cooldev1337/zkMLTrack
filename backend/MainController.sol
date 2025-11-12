// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * Prototype controller that lets you:
 *  - create tasks (datasets with Merkle roots)
 *  - initialize an evaluation for a verifier (N samples)
 *  - submit sample-by-sample inclusion verifications (one tx per sample)
 *  - compute accuracy when all samples are submitted and update best model if better
 *
 * Uses OpenZeppelin Ownable and ReentrancyGuard best practices and MerkleProof util.
 */

import "openzeppelin-contracts/contracts/access/Ownable.sol";
import "openzeppelin-contracts/contracts/utils/ReentrancyGuard.sol";
import "openzeppelin-contracts/contracts/utils/cryptography/MerkleProof.sol";

contract MainControllerPrototype is Ownable, ReentrancyGuard {

    /* ========== EVENTS ========== */

    event TaskCreated(uint256 indexed taskId, bytes32 merkleRoot, address indexed creator);
    event TaskMerkleRootUpdated(uint256 indexed taskId, bytes32 newRoot, address indexed updater);

    event EvaluationStarted(uint256 indexed taskId, address indexed verifier, uint256 totalToVerify, address indexed starter);
    event SampleVerified(uint256 indexed taskId, address indexed verifier, bool correct, uint256 totalVerified, uint256 correctSoFar);
    event EvaluationFinalized(uint256 indexed taskId, address indexed verifier, uint256 accuracyBp, uint256 correct, uint256 total);
    event BestVerifierUpdated(uint256 indexed taskId, address indexed verifier, uint256 newAccuracyBp);
    event EvaluationReset(uint256 indexed taskId, address indexed verifier, address indexed caller);

    /* ========== STRUCTS & STATE ========== */

    struct Task {
        bytes32 datasetMerkleRoot;
        address bestVerifier;
        uint256 bestAccuracy; // basis points (0..10000)
        bool exists;
    }

    struct EvaluationProgress {
        uint256 totalToVerify;    // expected N (set once when starting evaluation)
        uint256 totalSubmitted;   // how many samples submitted so far
        uint256 correctSamples;   // how many correct so far
        bool finalized;           // whether evaluation finished
        address starter;          // who started the evaluation (informational)
    }

    // taskId -> Task
    mapping(uint256 => Task) public tasks;

    // taskId -> verifier -> EvaluationProgress
    mapping(uint256 => mapping(address => EvaluationProgress)) public evaluations;

    // taskId -> verifier -> registered flag (finalized registration)
    mapping(uint256 => mapping(address => bool)) public verifierRegistered;

    /* ========== MODIFIERS ========== */

    modifier taskExists(uint256 taskId) {
        require(tasks[taskId].exists, "Task not found");
        _;
    }

    /* ========== CONSTRUCTOR ========== */

    /// @notice Ownable sets deployer as owner automatically (OpenZeppelin behavior).
    constructor() Ownable(msg.sender) {}

    /* ========== TASK MANAGEMENT (ADMIN) ========== */

    /**
     * @notice Create a new task (only owner)
     * @param taskId unique id for the task
     * @param merkleRoot bytes32 merkle root for validation dataset
     */
    function createTask(uint256 taskId, bytes32 merkleRoot) external onlyOwner {
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
     * @notice Update a task's Merkle root (only owner)
     * @param taskId id
     * @param newRoot new merkle root
     */
    function updateTaskMerkleRoot(uint256 taskId, bytes32 newRoot) external onlyOwner taskExists(taskId) {
        require(newRoot != bytes32(0), "Invalid merkle root");
        tasks[taskId].datasetMerkleRoot = newRoot;
        emit TaskMerkleRootUpdated(taskId, newRoot, msg.sender);
    }

    /* ========== EVALUATION LIFECYCLE ========== */

    /**
     * @notice Start an evaluation for a given verifier and task. Sets N (`totalToVerify`) once.
     * @dev This must be called before submitting sample proofs. Anyone can call it to start, but it cannot be changed until reset.
     * @param taskId id of the task
     * @param verifier address of the model/verifier contract
     * @param totalToVerify N samples you will submit (must be > 0)
     */
    function startEvaluation(uint256 taskId, address verifier, uint256 totalToVerify) external taskExists(taskId) {
        require(verifier != address(0), "Invalid verifier");
        require(verifier.code.length > 0, "Verifier must be contract");
        require(totalToVerify > 0, "totalToVerify must be > 0");

        EvaluationProgress storage ev = evaluations[taskId][verifier];
        require(!ev.finalized, "Evaluation already finalized");
        require(ev.totalToVerify == 0, "Evaluation already started");

        ev.totalToVerify = totalToVerify;
        ev.totalSubmitted = 0;
        ev.correctSamples = 0;
        ev.finalized = false;
        ev.starter = msg.sender;

        emit EvaluationStarted(taskId, verifier, totalToVerify, msg.sender);
    }

    /**
     * @notice Submit a single sample's inclusion proof and whether it was correct.
     * @dev This function is intended to be called sample-by-sample. Uses MerkleProof.verify for inclusion.
     * @param taskId dataset task id
     * @param verifier model verifier address (identifier)
     * @param leaf leaf hash for the sample (must match how dataset leaves are constructed off-chain)
     * @param proof merkle sibling array proving inclusion
     * @param correct true if the model predicted label correctly for this leaf
     */
    function submitSampleProof(
        uint256 taskId,
        address verifier,
        bytes32 leaf,
        bytes32[] calldata proof,
        bool correct
    ) external nonReentrant taskExists(taskId) {
        require(verifier != address(0), "Invalid verifier");

        EvaluationProgress storage ev = evaluations[taskId][verifier];
        require(!ev.finalized, "Evaluation finalized");
        require(ev.totalToVerify > 0, "Evaluation not started");

        // Verify inclusion against the stored Merkle root
        bytes32 root = tasks[taskId].datasetMerkleRoot;
        bool ok = MerkleProof.verify(proof, root, leaf);
        require(ok, "Invalid Merkle proof");

        // Update counters
        ev.totalSubmitted += 1;
        if (correct) {
            ev.correctSamples += 1;
        }

        emit SampleVerified(taskId, verifier, correct, ev.totalSubmitted, ev.correctSamples);

        // If reached expected total, finalize
        if (ev.totalSubmitted >= ev.totalToVerify) {
            ev.finalized = true;

            // compute accuracy in basis points (0..10000)
            uint256 accuracyBp = (ev.correctSamples * 10000) / ev.totalToVerify;

            // mark registered if better than previous best
            Task storage t = tasks[taskId];
            if (accuracyBp > t.bestAccuracy) {
                t.bestAccuracy = accuracyBp;
                t.bestVerifier = verifier;
                verifierRegistered[taskId][verifier] = true;
                emit BestVerifierUpdated(taskId, verifier, accuracyBp);
            }

            emit EvaluationFinalized(taskId, verifier, accuracyBp, ev.correctSamples, ev.totalToVerify);
        }
    }

    /**
     * @notice Reset an evaluation in case of error or to re-run (onlyOwner or task owner variant could be enforced).
     * @dev Allows restarting an evaluation for the same verifier/task. Resets counters.
     */
    function resetEvaluation(uint256 taskId, address verifier) external onlyOwner taskExists(taskId) {
        EvaluationProgress storage ev = evaluations[taskId][verifier];
        require(ev.totalToVerify > 0, "No evaluation to reset");
        // Reset state
        delete evaluations[taskId][verifier];
        emit EvaluationReset(taskId, verifier, msg.sender);
    }

    /* ========== VIEW HELPERS ========== */

    function getTask(uint256 taskId) external view taskExists(taskId) returns (bytes32 datasetRoot, address bestVerifier, uint256 bestAccuracy) {
        Task storage t = tasks[taskId];
        return (t.datasetMerkleRoot, t.bestVerifier, t.bestAccuracy);
    }

    function getEvaluation(uint256 taskId, address verifier) external view returns (uint256 totalToVerify, uint256 totalSubmitted, uint256 correctSamples, bool finalized, address starter) {
        EvaluationProgress storage ev = evaluations[taskId][verifier];
        return (ev.totalToVerify, ev.totalSubmitted, ev.correctSamples, ev.finalized, ev.starter);
    }

    function isVerifierRegistered(uint256 taskId, address verifier) external view returns (bool) {
        return verifierRegistered[taskId][verifier];
    }

}
