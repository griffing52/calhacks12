# Voice-focused imports - only import what's needed for voice calling
from .initiate_voice_call import initiate_voice_call

# Conditional imports for other tools (only if dependencies are available)
try:
    from .change_goal import change_goal
    from .create_invoice import create_invoice
    from .ecommerce.get_order import get_order
    from .ecommerce.list_orders import list_orders
    from .ecommerce.track_package import track_package
    from .fin.check_account_valid import check_account_valid
    from .fin.get_account_balances import get_account_balance
    from .fin.move_money import move_money
    from .fin.submit_loan_application import submit_loan_application
    from .find_events import find_events
    from .food.add_to_cart import add_to_cart
    from .give_hint import give_hint
    from .guess_location import guess_location
    from .hr.book_pto import book_pto
    from .hr.checkpaybankstatus import checkpaybankstatus
    from .hr.current_pto import current_pto
    from .hr.future_pto_calc import future_pto_calc
    from .list_agents import list_agents
    from .search_fixtures import search_fixtures
    from .search_flights import search_flights
    from .search_trains import book_trains, search_trains
    from .transfer_control import transfer_control
    
    _FULL_TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"Note: Some tools unavailable due to missing dependencies: {e}")
    print("Voice calling functionality will still work.")
    _FULL_TOOLS_AVAILABLE = False
    # Stub out missing tools
    change_goal = None
    create_invoice = None
    get_order = None
    list_orders = None
    track_package = None
    check_account_valid = None
    get_account_balance = None
    move_money = None
    submit_loan_application = None
    find_events = None
    add_to_cart = None
    give_hint = None
    guess_location = None
    book_pto = None
    checkpaybankstatus = None
    current_pto = None
    future_pto_calc = None
    list_agents = None
    search_fixtures = None
    search_flights = None
    search_trains = None
    book_trains = None
    transfer_control = None


def get_handler(tool_name: str):
    """Get handler for a tool by name. Raises ValueError if tool not found or unavailable."""
    # Voice calling tool (always available)
    if tool_name == "InitiateVoiceCall":
        return initiate_voice_call
    
    # Check if full tools are available
    if not _FULL_TOOLS_AVAILABLE:
        raise ValueError(
            f"Tool '{tool_name}' is not available. "
            "This application is configured for voice calling only. "
            "Install additional dependencies (pandas, stripe, etc.) to enable other tools."
        )
    
    # Other tools (require additional dependencies)
    if tool_name == "SearchFixtures":
        return search_fixtures
    if tool_name == "SearchFlights":
        return search_flights
    if tool_name == "SearchTrains":
        return search_trains
    if tool_name == "BookTrains":
        return book_trains
    if tool_name == "CreateInvoice":
        return create_invoice
    if tool_name == "FindEvents":
        return find_events
    if tool_name == "ListAgents":
        return list_agents
    if tool_name == "ChangeGoal":
        return change_goal
    if tool_name == "TransferControl":
        return transfer_control
    if tool_name == "CurrentPTO":
        return current_pto
    if tool_name == "BookPTO":
        return book_pto
    if tool_name == "FuturePTOCalc":
        return future_pto_calc
    if tool_name == "CheckPayBankStatus":
        return checkpaybankstatus
    if tool_name == "FinCheckAccountIsValid":
        return check_account_valid
    if tool_name == "FinCheckAccountBalance":
        return get_account_balance
    if tool_name == "FinMoveMoney":
        return move_money
    if tool_name == "FinCheckAccountSubmitLoanApproval":
        return submit_loan_application
    if tool_name == "GetOrder":
        return get_order
    if tool_name == "TrackPackage":
        return track_package
    if tool_name == "ListOrders":
        return list_orders
    if tool_name == "GiveHint":
        return give_hint
    if tool_name == "GuessLocation":
        return guess_location
    if tool_name == "AddToCart":
        return add_to_cart

    raise ValueError(f"Unknown tool: {tool_name}")
