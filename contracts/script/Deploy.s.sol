// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/VerityCommit.sol";

/// Usage:
///   source contracts/.env
///   forge script contracts/script/Deploy.s.sol \
///     --rpc-url $CHAIN_RPC_URL \
///     --private-key $DEPLOYER_PRIVATE_KEY \
///     --broadcast
contract Deploy is Script {
    function run() external {
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(pk);
        VerityCommit vc = new VerityCommit();
        console.log("VerityCommit deployed at:", address(vc));
        console.log("Update shared.env.example -> VERITY_COMMIT_ADDRESS");
        vm.stopBroadcast();
    }
}
