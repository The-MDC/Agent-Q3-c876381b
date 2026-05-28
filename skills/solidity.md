---
name: solidity
description: Solidity smart contract development, EVM patterns, on-chain prediction market contracts, and security auditing
triggers: [solidity, smart contract, evm, web3, vyper, hardhat, foundry, abi, contract audit, on-chain, defi, openzeppelin, ethereum, polygon, base, arbitrum]
roles: [coder, coder_dedicated, reasoner]
---

## When to activate
User asks to write, review, audit, or explain Solidity contracts or any EVM-compatible smart contract work.

## Solidity version matrix
| Version | Key features | Use for |
|---------|-------------|---------|
| ^0.8.20 | custom errors, `unchecked`, `immutable` | new contracts (default) |
| ^0.8.17 | `push0` opcode | L2-optimised |
| ^0.8.0  | built-in overflow checks | minimum safe baseline |

Always pin the version with `pragma solidity ^0.8.20;` unless the target chain requires otherwise.

## Standard patterns (use OpenZeppelin where available)

### Ownership & access
```solidity
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
```

### Reentrancy guard (mandatory for any external call that transfers value)
```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
// Apply modifier: nonReentrant
```

### Safe arithmetic
Built-in from 0.8.x — no SafeMath needed. Use `unchecked {}` only where overflow is impossible.

### Prediction market contract skeleton (binary outcome, Polymarket-compatible)
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IConditionalTokens {
    function prepareCondition(address oracle, bytes32 questionId, uint outcomeSlotCount) external;
    function reportPayouts(bytes32 questionId, uint[] calldata payouts) external;
}

contract PredictionMarket is ReentrancyGuard, Ownable {
    IConditionalTokens public immutable ctf;
    bytes32 public immutable conditionId;

    constructor(address _ctf, bytes32 _conditionId) {
        ctf = IConditionalTokens(_ctf);
        conditionId = _conditionId;
    }

    function resolve(uint[] calldata payouts) external onlyOwner {
        ctf.reportPayouts(conditionId, payouts);
    }
}
```

## ABI encoding
```solidity
// Encode function call
bytes memory data = abi.encodeWithSelector(IERC20.transfer.selector, recipient, amount);
// Decode return
(bool success, bytes memory result) = target.call(data);
require(success, "call failed");
uint256 val = abi.decode(result, (uint256));
```

## Gas optimisation checklist
- Use `calldata` instead of `memory` for read-only function parameters
- Pack storage variables (bool + uint96 + address fit in one slot)
- Prefer `++i` over `i++` in loops
- Use `custom errors` instead of `require(false, "string")`
- Mark constants `immutable` if set once in constructor, `constant` if compile-time known

## Security audit checklist (SWC registry)
- [ ] SWC-107: Reentrancy — use checks-effects-interactions + ReentrancyGuard
- [ ] SWC-101: Integer overflow — handled by 0.8.x; verify `unchecked` blocks
- [ ] SWC-115: tx.origin auth — never use `tx.origin` for authorisation
- [ ] SWC-104: Unchecked return values — always check `.call()` return
- [ ] SWC-116: Block values as time source — avoid `block.timestamp` for short windows
- [ ] SWC-131: Unused variables — compiler warning, check for hidden logic
- [ ] Access control — every privileged function should have a role check
- [ ] Oracle manipulation — use TWAP for price feeds, not spot price

## Test harness

### Foundry (preferred)
```bash
forge init && forge test -vvv
# Fuzz test example
function testFuzz_transfer(uint96 amount) public { ... }
```

### Hardhat
```bash
npx hardhat test --network hardhat
```

## Delegation
For contract implementation tasks, call the coder service:
```
POST http://coder:8001/v1/coder
{
  "task": "implement solidity contract",
  "context": "<requirements>",
  "model": "qwen3-coder-53b:q6_k"
}
```
Use Kimi-Linear for long-context contract analysis (1M ctx handles large codebases + audit reports).
