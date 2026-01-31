import { BigInt, Address, log } from "@graphprotocol/graph-ts";
import { Transfer as TransferEvent } from "../generated/ERC20/ERC20";
import { ERC20 } from "../generated/ERC20/ERC20";
import {
  Token,
  Account,
  AccountBalance,
  BalanceSnapshot,
  Transfer,
} from "../generated/schema";

// Constants
const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const ZERO_BI = BigInt.fromI32(0);
const ONE_BI = BigInt.fromI32(1);

/**
 * Get or create a Token entity
 */
function getOrCreateToken(address: Address): Token {
  let id = address.toHexString();
  let token = Token.load(id);

  if (token == null) {
    token = new Token(id);

    // Try to fetch token metadata from contract
    let contract = ERC20.bind(address);

    let nameResult = contract.try_name();
    token.name = nameResult.reverted ? "Unknown" : nameResult.value;

    let symbolResult = contract.try_symbol();
    token.symbol = symbolResult.reverted ? "???" : symbolResult.value;

    let decimalsResult = contract.try_decimals();
    token.decimals = decimalsResult.reverted ? 18 : decimalsResult.value;

    let totalSupplyResult = contract.try_totalSupply();
    token.totalSupply = totalSupplyResult.reverted ? ZERO_BI : totalSupplyResult.value;

    token.holderCount = ZERO_BI;
    token.save();
  }

  return token;
}

/**
 * Get or create an Account entity
 */
function getOrCreateAccount(address: Address): Account {
  let id = address.toHexString();
  let account = Account.load(id);

  if (account == null) {
    account = new Account(id);
    account.save();
  }

  return account;
}

/**
 * Get or create an AccountBalance entity
 */
function getOrCreateAccountBalance(
  account: Account,
  token: Token
): AccountBalance {
  let id = account.id + "-" + token.id;
  let balance = AccountBalance.load(id);

  if (balance == null) {
    balance = new AccountBalance(id);
    balance.account = account.id;
    balance.token = token.id;
    balance.balance = ZERO_BI;
    balance.blockNumber = ZERO_BI;
    balance.timestamp = ZERO_BI;
  }

  return balance;
}

/**
 * Create a balance snapshot for historical tracking
 */
function createBalanceSnapshot(
  account: Account,
  token: Token,
  balance: BigInt,
  blockNumber: BigInt,
  timestamp: BigInt
): void {
  let id = account.id + "-" + token.id + "-" + blockNumber.toString();
  let snapshot = new BalanceSnapshot(id);

  snapshot.account = account.id;
  snapshot.token = token.id;
  snapshot.balance = balance;
  snapshot.blockNumber = blockNumber;
  snapshot.timestamp = timestamp;

  snapshot.save();
}

/**
 * Handle ERC-20 Transfer events
 * This is the main entry point for indexing
 */
export function handleTransfer(event: TransferEvent): void {
  let token = getOrCreateToken(event.address);
  let from = getOrCreateAccount(event.params.from);
  let to = getOrCreateAccount(event.params.to);

  let blockNumber = event.block.number;
  let timestamp = event.block.timestamp;
  let amount = event.params.value;

  // Create Transfer entity
  let transferId =
    event.transaction.hash.toHexString() + "-" + event.logIndex.toString();
  let transfer = new Transfer(transferId);

  transfer.token = token.id;
  transfer.from = from.id;
  transfer.to = to.id;
  transfer.amount = amount;
  transfer.blockNumber = blockNumber;
  transfer.timestamp = timestamp;
  transfer.transactionHash = event.transaction.hash;
  transfer.logIndex = event.logIndex;

  transfer.save();

  // Update sender balance (skip for mints from zero address)
  if (event.params.from.toHexString() != ZERO_ADDRESS) {
    let fromBalance = getOrCreateAccountBalance(from, token);
    let previousFromBalance = fromBalance.balance;

    fromBalance.balance = fromBalance.balance.minus(amount);
    fromBalance.blockNumber = blockNumber;
    fromBalance.timestamp = timestamp;
    fromBalance.save();

    // Create snapshot for historical tracking
    createBalanceSnapshot(from, token, fromBalance.balance, blockNumber, timestamp);

    // Update holder count if balance went to zero
    if (previousFromBalance.gt(ZERO_BI) && fromBalance.balance.equals(ZERO_BI)) {
      token.holderCount = token.holderCount.minus(ONE_BI);
    }
  }

  // Update receiver balance (skip for burns to zero address)
  if (event.params.to.toHexString() != ZERO_ADDRESS) {
    let toBalance = getOrCreateAccountBalance(to, token);
    let previousToBalance = toBalance.balance;

    toBalance.balance = toBalance.balance.plus(amount);
    toBalance.blockNumber = blockNumber;
    toBalance.timestamp = timestamp;
    toBalance.save();

    // Create snapshot for historical tracking
    createBalanceSnapshot(to, token, toBalance.balance, blockNumber, timestamp);

    // Update holder count if this is a new holder
    if (previousToBalance.equals(ZERO_BI) && toBalance.balance.gt(ZERO_BI)) {
      token.holderCount = token.holderCount.plus(ONE_BI);
    }
  }

  // Update token total supply for mints/burns
  if (event.params.from.toHexString() == ZERO_ADDRESS) {
    // Mint
    token.totalSupply = token.totalSupply.plus(amount);
  } else if (event.params.to.toHexString() == ZERO_ADDRESS) {
    // Burn
    token.totalSupply = token.totalSupply.minus(amount);
  }

  token.save();

  log.info("Transfer: {} -> {} amount: {} token: {}", [
    from.id,
    to.id,
    amount.toString(),
    token.symbol,
  ]);
}
