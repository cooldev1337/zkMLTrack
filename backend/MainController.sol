// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "openzeppelin-contracts/contracts/access/Ownable.sol";
import "openzeppelin-contracts/contracts/utils/cryptography/MerkleProof.sol";

/**
 * @title MainController
 * @notice Manages AI model verifiers and tracks best accuracy
 * @dev Stores validation dataset Merkle root and verifier registry
 */
contract MainController is Ownable {
    
    // State variables
    bytes32 public validationDatasetMerkleRoot;
    address public bestVerifier;
    uint256 public bestAccuracy; // Basis points (9500 = 95%)
    
    // Verifier info
    struct Verifier {
        uint256 accuracy;
        address owner;
        bool exists;
    }
    
    mapping(address => Verifier) public verifiers;
    
    // Events
    event VerifierRegistered(address indexed verifier, address indexed owner, uint256 accuracy);
    event BestVerifierUpdated(address indexed verifier, uint256 accuracy);
    
    constructor(bytes32 _merkleRoot) Ownable(msg.sender) {
        require(_merkleRoot != bytes32(0), "Invalid Merkle root");
        validationDatasetMerkleRoot = _merkleRoot;
    }
    
    /**
     * @notice Register a new verifier contract
     * @param _verifier Address of the verifier contract
     * @param _accuracy Accuracy in basis points (0-10000)
     */
    function registerVerifier(address _verifier, uint256 _accuracy) external {
        require(_verifier != address(0), "Invalid verifier address");
        require(_accuracy <= 10000, "Accuracy must be <= 100%");
        require(!verifiers[_verifier].exists, "Verifier already registered");
        
        verifiers[_verifier] = Verifier({
            accuracy: _accuracy,
            owner: msg.sender,
            exists: true
        });
        
        emit VerifierRegistered(_verifier, msg.sender, _accuracy);
        
        // Update best verifier if needed
        if (_accuracy > bestAccuracy) {
            bestVerifier = _verifier;
            bestAccuracy = _accuracy;
            emit BestVerifierUpdated(_verifier, _accuracy);
        }
    }
    
    /**
     * @notice Update Merkle root (owner only)
     * @param _newMerkleRoot New Merkle root
     */
    function updateMerkleRoot(bytes32 _newMerkleRoot) external onlyOwner {
        require(_newMerkleRoot != bytes32(0), "Invalid Merkle root");
        validationDatasetMerkleRoot = _newMerkleRoot;
    }
    
    /**
     * @notice Verify a data sample is in the validation dataset
     * @param _leaf Hash of the data sample
     * @param _proof Merkle proof
     * @return bool True if valid
     */
    function verifyDataSample(bytes32 _leaf, bytes32[] calldata _proof) 
        external 
        view 
        returns (bool) 
    {
        return MerkleProof.verify(_proof, validationDatasetMerkleRoot, _leaf);
    }
    
    /**
     * @notice Get best verifier info
     * @return address Best verifier address
     * @return uint256 Best accuracy
     */
    function getBestVerifier() external view returns (address, uint256) {
        return (bestVerifier, bestAccuracy);
    }
}