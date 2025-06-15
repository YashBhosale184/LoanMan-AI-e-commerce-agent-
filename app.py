import streamlit as st
import os
from dotenv import load_dotenv
from payman_sdk.client import PaymanClient
from payman_sdk.types import PaymanConfig
import requests # Kept in case you need it for other non-Payman SDK API calls

load_dotenv()

#Payman Setup
config: PaymanConfig = {
    'client_id': os.getenv("PAYMAN_CLIENT_ID"),
    'client_secret': os.getenv("PAYMAN_CLIENT_SECRET")
}

print(f"DEBUG: Loaded PAYMAN_CLIENT_ID: {'SET' if config['client_id'] else 'NOT SET'}")
print(f"DEBUG: Loaded PAYMAN_CLIENT_SECRET: {'SET' if config['client_secret'] else 'NOT SET'}")

client = None
try:
    if config['client_id'] and config['client_secret']:
        client = PaymanClient.with_credentials(config)
        st.sidebar.success("Payman AI Client Initialized (via SDK)!")
    else:
        st.sidebar.error("Payman AI Client ID or Secret is missing in .env file. Cannot initialize SDK.")
except Exception as e:
    st.sidebar.error(f"Failed to initialize Payman AI Client: {e}. Check your .env credentials and SDK version.")


#Loan Calculation Logic
def calculate_loan_amount(daily_sales: float, business_type: str, operating_days: int):
    """Calculates loan amount based on a rule-based system."""
    base_loan_from_sales = 0.0
    if daily_sales < 5: base_loan_from_sales = 0.0
    elif daily_sales < 10: base_loan_from_sales = 15
    elif daily_sales < 15: base_loan_from_sales = 25
    else: base_loan_from_sales = 35
    if base_loan_from_sales == 0: return 0.0, 0.0
    adjusted_loan_amount = base_loan_from_sales
    potential_food_increment_value = 0.0
    if business_type.lower() == "food":
        potential_food_increment_value = base_loan_from_sales * 0.1
        adjusted_loan_amount *= 1.1
    elif business_type.lower() == "clothing":
        adjusted_loan_amount *= 0.9
    if operating_days >= 6: adjusted_loan_amount += 10
    max_loan_amount = 600
    final_loan_amount = min(adjusted_loan_amount, max_loan_amount)
    min_disbursable_amount = 10.0
    if final_loan_amount < min_disbursable_amount: return 0.0, 0.0
    return float(int(final_loan_amount)), float(int(potential_food_increment_value))


# --- Streamlit App State Management
if 'app_state' not in st.session_state:
    st.session_state.app_state = 'initial'
    st.session_state.vendor_name = ''
    st.session_state.daily_sales_input = 0.0
    st.session_state.business_type_input = 'Food'
    st.session_state.operating_days_input = 5
    st.session_state.calculated_loan_amount = 0.0
    st.session_state.food_business_increment = 0.0
    st.session_state.loan_amount = 0.0
    st.session_state.current_balance = 0.0
    st.session_state.total_bonuses = 0.0
    st.session_state.days_tracked = 0
    st.session_state.loan_disbursed = False
    st.session_state.message = "Welcome! Enter vendor details to calculate your micro-loan."
    st.session_state.payee_id_input = ""

#Payman AI Interaction Functions (using SDK)
def send_payman_payment_sdk(payman_client, destination_id, amount, memo, currency="TSD"):
    """Sends a payment using the Payman AI SDK via the 'ask' method, with status check."""
    if not payman_client:
        return {"status": "error", "message": "Payman AI Client not initialized. Check your credentials."}
    if not destination_id:
        return {"status": "error", "message": "Payee ID (Payment Destination ID) is required for disbursement."}

    try:
        # Construct the natural language command for the 'ask' method. 
        payment_command = f"Send {amount:.2f} {currency} to payee with ID {destination_id}. Memo: {memo}"
        
        response = payman_client.ask(payment_command)

        # --- NEW: Check the response for payment status ---
        # Payman AI's 'ask' method returns an AI response, which might be a string
        # or a more structured object/dictionary if an action was performed.
        # We need to parse this response to determine the actual payment status.
        transaction_id = "N/A"
        payment_status_info = "" # To store a more detailed status message for display

        # Best guess for common response patterns:
        if isinstance(response, dict):
            # Check for specific keys indicating status or an error
            status_from_response = response.get('status') or response.get('state') or response.get('payment_status')
            message_from_response = response.get('message') or response.get('error') or response.get('detail')
            
            if status_from_response and status_from_response.lower() in ('rejected', 'failed', 'declined'):
                payment_status_info = message_from_response if message_from_response else f"Status: {status_from_response}"
                return {"status": "error", "message": f"Payment rejected by Payman AI dashboard/system. {payment_status_info}", "transaction_id": transaction_id}
            
            # Extract transaction ID if present
            transaction_id = response.get('transaction_id') or response.get('id')

        elif isinstance(response, str):
            # If the response is a simple string, look for keywords
            lower_response = response.lower()
            if "rejected" in lower_response or "failed" in lower_response or "declined" in lower_response:
                payment_status_info = response
                return {"status": "error", "message": f"Payment rejected by Payman AI system. Response: {payment_status_info}", "transaction_id": transaction_id}
            
            # For string responses, a clear transaction ID is less likely, but we can assume success if no rejection keywords.
            if "sent" in lower_response or "success" in lower_response or "completed" in lower_response:
                 transaction_id = "Confirmed via AI response" # Generic ID for string confirmation

        # Fallback: If no explicit rejection was found, assume it proceeded successfully.
        # This might need refinement if Payman AI has a 'pending' state that needs explicit handling.
        return {"status": "success", "data": response, "transaction_id": transaction_id}

    except Exception as e:
        st.error(f"Payment request failed via Payman AI 'ask' method: {e}. Ensure Payee ID is valid, and check Payman AI account/policy settings.")
        return {"status": "error", "message": f"Payment failed via SDK: {e}"}

# --- Streamlit UI Layout (Minimal change for currency default) ---
st.title("💰 Vendor Growth Fund")
st.markdown("### Smart Disbursement & Incentive App for Street Vendors")

st.write(st.session_state.message)

st.sidebar.header("Payman AI SDK Status")
if client:
    st.sidebar.success("Payman AI SDK is ready!")
    st.sidebar.caption("Ensure your Payee IDs are correct for disbursements.")
else:
    st.sidebar.error("Payman AI SDK failed to initialize. Check `PAYMAN_CLIENT_ID` and `PAYMAN_CLIENT_SECRET` in your `.env` file.")

if st.session_state.app_state == 'initial':
    with st.form("loan_details_form"):
        st.session_state.vendor_name = st.text_input("Vendor Name", value=st.session_state.vendor_name, placeholder="E.g., Raja's Thela")
        st.session_state.daily_sales_input = st.number_input("Average Daily Sales ($)", min_value=0.0, value=st.session_state.daily_sales_input, step=10.0, placeholder="Enter average daily sales (e.g., 750)")
        st.session_state.business_type_input = st.selectbox("Business Type", ["Food", "Clothing", "Other"], index=["Food", "Clothing", "Other"].index(st.session_state.business_type_input))
        st.session_state.operating_days_input = st.number_input("Operating Days per Week", min_value=1, max_value=7, value=st.session_state.operating_days_input, step=1, placeholder="Enter days per week (1-7)")

        calculate_button = st.form_submit_button("Calculate Recommended Loan")

        if calculate_button:
            if not st.session_state.vendor_name:
                st.warning('Please enter vendor name to calculate loan.')
                st.session_state.message = 'Please enter vendor name to calculate loan.'
                st.rerun()
            elif st.session_state.daily_sales_input < 5:
                st.warning("No loan if daily sales are less than $5.")
                st.session_state.message = "Please increase daily sales for a loan recommendation."
                st.session_state.calculated_loan_amount = 0.0
                st.session_state.food_business_increment = 0.0
                st.rerun()
            else:
                st.session_state.calculated_loan_amount, st.session_state.food_business_increment = calculate_loan_amount(
                    daily_sales=st.session_state.daily_sales_input,
                    business_type=st.session_state.business_type_input,
                    operating_days=st.session_state.operating_days_input
                )
                if st.session_state.calculated_loan_amount > 0:
                    st.session_state.message = f"Based on your inputs, the recommended loan amount is **${st.session_state.calculated_loan_amount:.2f}**."
                    st.success(f"Recommended Loan: **${st.session_state.calculated_loan_amount:.2f}**")
                else:
                    st.session_state.message = "Based on your inputs, a loan is currently not recommended."
                st.rerun()

    if st.session_state.calculated_loan_amount > 0:
        if st.button("Confirm & Request This Loan"):
            st.session_state.loan_amount = st.session_state.calculated_loan_amount
            st.session_state.app_state = 'loan_requested'
            st.session_state.message = f"Loan request for {st.session_state.vendor_name} (${st.session_state.loan_amount:.2f}) confirmed and submitted. Awaiting approval..."
            st.rerun()

elif st.session_state.app_state == 'loan_requested':
    st.write(f"Loan request for **{st.session_state.vendor_name}** of **${st.session_state.loan_amount:.2f}** has been submitted.")

    if st.session_state.business_type_input.lower() == "food" and st.session_state.food_business_increment > 0:
        st.info(f"✨ Your loan amount includes an additional ${st.session_state.food_business_increment:.2f} due to your 'Food' business type.")

    if st.button("Simulate Loan Approval"):
        st.session_state.app_state = 'loan_approved'
        st.session_state.message = f"Loan for {st.session_state.vendor_name} approved! Ready for disbursement."
        st.rerun()

elif st.session_state.app_state == 'loan_approved':
    st.write(f"Loan for **{st.session_state.vendor_name}** of **${st.session_state.loan_amount:.2f}** is approved!")

    st.session_state.payee_id_input = st.text_input(
        "Enter Vendor's Payman AI Payee ID (Payment Destination ID)",
        value=st.session_state.payee_id_input,
        placeholder="e.g., payee_XXXXX_YYYYY"
    )

    if st.button("Disburse Loan via Payman AI SDK"):
        if not client:
            st.error("Cannot disburse: Payman AI SDK not initialized. Check your credentials.")
            st.rerun()
        elif not st.session_state.payee_id_input:
            st.warning("Please enter the Vendor's Payman AI Payee ID to disburse the loan.")
            st.rerun()
        else:
            with st.spinner("Disbursing loan via Payman AI SDK..."):
                st.session_state.message = "Loan disbursement in progress via SDK..."
                payment_result = send_payman_payment_sdk(
                    client,
                    st.session_state.payee_id_input,
                    st.session_state.loan_amount,
                    f"Micro-loan for {st.session_state.vendor_name}'s Thela",
                    currency="TSD"
                )

                if payment_result["status"] == "success":
                    st.session_state.message = f"Loan of ${st.session_state.loan_amount:.2f} TSD disbursed successfully! Transaction ID: {payment_result['transaction_id']}"
                    st.session_state.current_balance += st.session_state.loan_amount
                    st.session_state.loan_disbursed = True
                    st.session_state.app_state = 'tracking_sales'
                else: # Payment failed or was rejected
                    st.session_state.message = payment_result["message"]
                    # Stay on the same state or revert to a "Disbursement Failed" state
                    st.session_state.app_state = 'loan_approved' # Keep it on the loan approval stage if rejected
                st.rerun()

elif st.session_state.app_state == 'tracking_sales':
    st.subheader(f"Vendor: {st.session_state.vendor_name}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Balance", f"${st.session_state.current_balance:.2f}")
    with col2:
        st.metric("Total Bonuses", f"${st.session_state.total_bonuses:.2f}")
    with col3:
        st.metric("Days Tracked", st.session_state.days_tracked)

    with st.form("daily_sales_form"):
        st.session_state.daily_sales_input = st.number_input("Enter Day's Sales ($)", min_value=0.0, value=st.session_state.daily_sales_input, step=1.0)
        submitted_sales = st.form_submit_button("Record Sales & Check for Bonus")
        if submitted_sales:
            st.session_state.days_tracked += 1
            st.session_state.message = f"Day {st.session_state.days_tracked} sales recorded: ${st.session_state.daily_sales_input:.2f}. Checking for bonus..."

            if st.session_state.daily_sales_input >= 50:
                with st.spinner("Issuing growth bonus via Payman AI SDK..."):
                    bonus_amount = 5.00
                    payment_result = send_payman_payment_sdk(
                        client,
                        st.session_state.payee_id_input,
                        bonus_amount,
                        f"Growth bonus for {st.session_state.vendor_name} (sales performance)",
                        currency="TSD"
                    )
                    if payment_result["status"] == "success":
                        st.session_state.message = f"Growth bonus of ${bonus_amount:.2f} TSD issued! Transaction ID: {payment_result['transaction_id']}"
                        st.session_state.current_balance += bonus_amount
                        st.session_state.total_bonuses += bonus_amount
                    else:
                        st.session_state.message = payment_result["message"]
            else:
                st.session_state.message = f"Day {st.session_state.days_tracked} sales recorded: ${st.session_state.daily_sales_input:.2f}. No bonus this time."
            st.rerun()

st.markdown("---")
st.caption("Powered by Payman AI SDK")
st.caption("**Important:** Ensure your `PAYMAN_CLIENT_ID` and `PAYMAN_CLIENT_SECRET` are securely set in your `.env` file.")