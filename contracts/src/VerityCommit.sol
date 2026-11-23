// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title VerityCommit
/// @notice Append-only commitment log for Verity Care fraud-detection claims.
///         Each claim type corresponds to a different trust assertion:
///           1 (TAP)              - a nurse NFC tap, anchored at capture time by phantom-shift.
///           2 (VOICE)            - a resident voice attestation, anchored at end-of-call.
///           3 (CASEFILE)         - a final MFCU referral packet, anchored at export time.
///           4 (SIGNAL_CARD)      - a per-signal computation result, anchored at compute time.
///           5 (PROOF_OF_SERVICE) - a staff-delivered service event (meal, dose, visit) with
///                                  photo + metadata CID on IPFS, anchored at delivery time.
///         Only hashes are stored; preimages stay off-chain. No PHI ever touches this contract.
contract VerityCommit {
    uint8 public constant CLAIM_TAP = 1;
    uint8 public constant CLAIM_VOICE = 2;
    uint8 public constant CLAIM_CASEFILE = 3;
    uint8 public constant CLAIM_SIGNAL_CARD = 4;
    uint8 public constant CLAIM_PROOF_OF_SERVICE = 5;

    /// @notice Emitted on every commit. Index all three main fields for cheap querying.
    event Committed(
        uint8 indexed claimType,
        bytes32 indexed claimHash,
        address indexed committer,
        uint64 timestamp
    );

    /// @notice Commit a claim hash. Idempotent at the hash level — the same hash can be committed
    ///         by different committers for different claim types, but the chain-of-custody
    ///         query uses (committer, claimType, timestamp) to disambiguate.
    /// @param claimType One of CLAIM_* constants above.
    /// @param claimHash Opaque 32-byte digest of the off-chain preimage.
    function commit(uint8 claimType, bytes32 claimHash) external {
        require(claimType >= 1 && claimType <= 5, "VerityCommit: unknown claim type");
        require(claimHash != bytes32(0), "VerityCommit: empty hash");
        emit Committed(claimType, claimHash, msg.sender, uint64(block.timestamp));
    }
}
