import os
from dotenv import load_dotenv
from pathlib import Path
from game_sdk.game.agent import Agent, WorkerConfig
from game_sdk.game.custom_types import FunctionResult
from onchain_actions_game_sdk.onchain_actions import get_onchain_actions
from goat_plugins.erc20.token import PEPE, USDC
from goat_plugins.erc20 import ERC20PluginOptions, erc20
from web3 import Web3
from web3.middleware.signing import construct_sign_and_send_raw_middleware
from eth_account.signers.local import LocalAccount
from eth_account import Account
from goat_plugins.uniswap import uniswap, UniswapPluginOptions
from goat_wallets.web3 import Web3EVMWalletClient
from goat_plugins.dexscreener import DexscreenerPluginOptions, dexscreener
from goat_plugins.twitter import twitter, TwitterPluginOptions
from goat_plugins.market_analysis import market_analysis, MarketAnalysisPluginOptions


# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

def get_agent_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    """
    Update state based on the function results
    """
    init_state = {}

    if current_state is None:
        return init_state

    if function_result.info is not None:
        # Update state with the function result info
        current_state.update(function_result.info)

    return current_state

def get_worker_state(function_result: FunctionResult, current_state: dict) -> dict:
    """
    Update state based on the function results
    """
    init_state = {}

    if current_state is None:
        return init_state

    if function_result.info is not None:
        # Update state with the function result info
        current_state.update(function_result.info)

    return current_state


# Initialize Web3 and account
w3 = Web3(Web3.HTTPProvider(os.environ.get("RPC_PROVIDER_URL")))
private_key = os.environ.get("WALLET_PRIVATE_KEY")
assert private_key is not None, "You must set WALLET_PRIVATE_KEY environment variable"
assert private_key.startswith("0x"), "Private key must start with 0x hex prefix"

account: LocalAccount = Account.from_key(private_key)
w3.eth.default_account = account.address  # Set the default account
w3.middleware_onion.add(
    construct_sign_and_send_raw_middleware(account)
)  # Add middleware

# Initialize tools with web3 wallet and Uniswap plugin
uniswap_api_key = os.environ.get("UNISWAP_API_KEY")
uniswap_base_url = os.environ.get("UNISWAP_BASE_URL", "https://trade-api.gateway.uniswap.org/v1")
assert uniswap_api_key is not None, "You must set UNISWAP_API_KEY environment variable"
assert uniswap_base_url is not None, "You must set UNISWAP_BASE_URL environment variable"

# Initialize plugins
twitter_plugin = twitter(options=TwitterPluginOptions(
    credentials_path="twitter_credentials.yaml",
    product="30day",
    environment="dev"
))

market_analysis_plugin = market_analysis(options=MarketAnalysisPluginOptions(
    openrouter_key=os.environ.get("OPENROUTER_API_KEY")
))

# Create action spaces
twitter_actions = get_onchain_actions(
    wallet=Web3EVMWalletClient(w3),
    plugins=[twitter_plugin],
)

market_analysis_actions = get_onchain_actions(
    wallet=Web3EVMWalletClient(w3),
    plugins=[market_analysis_plugin],
)

onchain_actions = get_onchain_actions(
    wallet=Web3EVMWalletClient(w3),
    plugins=[
        erc20(options=ERC20PluginOptions(tokens=[USDC, PEPE])),
        dexscreener(options=DexscreenerPluginOptions()),
        uniswap(options=UniswapPluginOptions(
            api_key=uniswap_api_key,
            base_url=uniswap_base_url
        )),
    ],
)

# Create workers
twitter_worker = WorkerConfig(
    id="twitter_worker",
    worker_description="Worker that searches for trending memecoins on Twitter",
    get_state_fn=get_worker_state,
    action_space=twitter_actions,
)

market_analysis_worker = WorkerConfig(
    id="market_analysis_worker",
    worker_description="Worker that analyzes market data for memecoins",
    get_state_fn=get_worker_state,
    action_space=market_analysis_actions,
)

onchain_actions_worker = WorkerConfig(
    id="onchain_actions_worker",
    worker_description="Worker that executes onchain actions such as swaps, transfers, etc.",
    get_state_fn=get_worker_state,
    action_space=onchain_actions,
)

# Initialize the agent
agent = Agent(
    api_key=os.environ.get("GAME_API_KEY"),
    name="Memecoin Analysis Agent",
    agent_goal="Find trending memecoins, analyze their market potential, and trade them to make money. If you are unable to find a coin on dexscreener, just go off of the twitter sentiment",
    agent_description=(
        "An agent that identifies trending memecoins on Twitter, analyzes their market data, "
        "and provides insights on their potential."
        "You are also able to directly trade these memecoins to make as much money as possible"
    ),
    get_agent_state_fn=get_agent_state_fn,
    workers=[
        twitter_worker,
        market_analysis_worker,
        onchain_actions_worker,
    ]
)

agent.compile()
agent.run()
