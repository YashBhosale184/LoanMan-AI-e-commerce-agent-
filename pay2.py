import streamlit as st
import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

# --- Payman AI API Configuration ---
# Get credentials from environment variables
# You now have your actual Client ID and Client Secret from Payman AI dashboard.
# IMPORTANT: Store these securely, ideally in your .env file or a secure vault.
# Use a more descriptive default value, or an empty string, if not found,
# to clearly indicate when the .env values aren't being loaded.
PAYMAN_CLIENT_ID = os.getenv("PAYMAN_CLIENT_ID")
PAYMAN_CLIENT_SECRET = os.getenv("PAYMAN_CLIENT_SECRET")

# --- Temporary Debug Print ---
# This will print the values that your app is actually using.
# REMOVE THESE LINES ONCE AUTHENTICATION IS SUCCESSFUL!
print(f"DEBUG: Client ID being used: {PAYMAN_CLIENT_ID}")
print(f"DEBUG: Client Secret being used: {PAYMAN_CLIENT_SECRET}")
# --- End Temporary Debug Print ---

# Payman AI API Endpoints
AUTH_URL = "https://api.paymanai.com/v1beta/auth/token"
SEND_PAYMENT_URL = "https://api.paymanai.com/v1beta/payments/send"
app_id="app-1f046b19-6b76-6c00-b4d8-3f7a70446e8f"

# --- Loan Calculation Logic ---
def calculate_loan_amount(daily_sales: float, business_type: str, operating_days: int):
    """Calculates loan amount based on a rule-based system.

    Args:
        daily_sales: The vendor's average daily sales (float).
        business_type: The type of business (string, e.g., "food", "clothing", "other").
        operating_days: Number of days the vendor operates in a week (int).

    Returns:
        A tuple: (recommended loan amount (float), potential food business increment (float)).
        Returns (0.0, 0.0) if no loan is recommended.
    """
    base_loan_from_sales = 0.0

    if daily_sales < 5:
        base_loan_from_sales = 0.0
    elif daily_sales < 10:
        base_loan_from_sales = 15
    elif daily_sales < 15:
        base_loan_from_sales = 25
    else:
        base_loan_from_sales = 35

    if base_loan_from_sales == 0:
        return 0.0, 0.0

    adjusted_loan_amount = base_loan_from_sales
    potential_food_increment_value = 0.0

    if business_type.lower() == "food":
        potential_food_increment_value = base_loan_from_sales * 0.1
        adjusted_loan_amount *= 1.1
    elif business_type.lower() == "clothing":
        adjusted_loan_amount *= 0.9

    if operating_days >= 6:
        adjusted_loan_amount += 10

    max_loan_amount = 600
    final_loan_amount = min(adjusted_loan_amount, max_loan_amount)

    min_disbursable_amount = 10.0
    if final_loan_amount < min_disbursable_amount:
        return 0.0, 0.0

    return float(int(final_loan_amount)), float(int(potential_food_increment_value))


# --- Streamlit App State Management ---
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
    # Initialize the new payee ID in session state
    st.session_state.payee_id_input = ""

# --- Payman AI Interaction Functions ---
def get_payman_access_token():
    """Obtains an access token from Payman AI using client credentials."""
    headers = {
        'Content-Type': 'application/json',
    }
    payload = {
        'clientId': PAYMAN_CLIENT_ID,
        'clientSecret': PAYMAN_CLIENT_SECRET,
        'grantType': 'client_credentials',
    }
    try:
        response = requests.post(AUTH_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['accessToken']
    except requests.exceptions.RequestException as e:
        st.error(f"Authentication error: {e}. Ensure your Payman AI Client ID and Client Secret are correct and have network access.")
        raise

def send_payman_payment(destination_id, amount, memo, currency="INR"):
    """Sends a payment using the Payman AI API via requests."""
    if not destination_id:
        return {"status": "error", "message": "Payee ID (Payment Destination ID) is required for disbursement."}
    try:
        access_token = get_payman_access_token()
    except Exception:
        return {"status": "error", "message": "Failed to authenticate with Payman AI. Check credentials."}

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
    }
    payload = {
        'paymentDestinationId': destination_id,
        'amountDecimal': float(amount),
        'memo': memo,
        'currency': currency,
    }
    try:
        response = requests.post(SEND_PAYMENT_URL, headers=headers, json=payload)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except requests.exceptions.RequestException as e:
        st.error(f"Payment request failed: {e}. Check Payee ID and Payman AI account balance.")
        return {"status": "error", "message": f"Payment failed: {e}"}
    
def send_payman_payment(destination_id, amount, memo, currency="INR"):
    if not destination_id:
        # This is where a Payee ID missing error would show up, but only if
        # authentication *succeeded* first.
        return {"status": "error", "message": "Payee ID (Payment Destination ID) is required for disbursement."}
    try:
        access_token = get_payman_access_token() # Authentication happens HERE
    except Exception:
        # If authentication fails, this error is returned:
        return {"status": "error", "message": "Failed to authenticate with Payman AI. Check credentials."}

# --- Streamlit UI Layout ---
st.title("💰 Vendor Growth Fund")
st.markdown("### Smart Disbursement & Incentive App for Street Vendors")

st.write(st.session_state.message)


if st.session_state.app_state == 'initial':
    with st.form("loan_details_form"):
        st.session_state.vendor_name = st.text_input("Vendor Name", value=st.session_state.vendor_name, placeholder="E.g., Raja's Thela")
        st.session_state.daily_sales_input = st.number_input("Average Daily Sales (₹)", min_value=0.0, value=st.session_state.daily_sales_input, step=10.0, placeholder="Enter average daily sales (e.g., 750)")
        st.session_state.business_type_input = st.selectbox("Business Type", ["Food", "Clothing", "Other"], index=["Food", "Clothing", "Other"].index(st.session_state.business_type_input))
        st.session_state.operating_days_input = st.number_input("Operating Days per Week", min_value=1, max_value=7, value=st.session_state.operating_days_input, step=1, placeholder="Enter days per week (1-7)")

        calculate_button = st.form_submit_button("Calculate Recommended Loan")

        if calculate_button:
            if not st.session_state.vendor_name:
                st.warning('Please enter vendor name to calculate loan.')
                st.session_state.message = 'Please enter vendor name to calculate loan.'
                st.rerun()
            elif st.session_state.daily_sales_input < 5:
                st.warning("No loan if daily sales are less than ₹5.")
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
                    st.session_state.message = f"Based on your inputs, the recommended loan amount is **₹{st.session_state.calculated_loan_amount:.2f}**."
                    st.success(f"Recommended Loan: **₹{st.session_state.calculated_loan_amount:.2f}**")
                else:
                    st.session_state.message = "Based on your inputs, a loan is currently not recommended."
                st.rerun()

    if st.session_state.calculated_loan_amount > 0:
        if st.button("Confirm & Request This Loan"):
            st.session_state.loan_amount = st.session_state.calculated_loan_amount
            st.session_state.app_state = 'loan_requested'
            st.session_state.message = f"Loan request for {st.session_state.vendor_name} (₹{st.session_state.loan_amount:.2f}) confirmed and submitted. Awaiting approval..."
            st.rerun()

elif st.session_state.app_state == 'loan_requested':
    st.write(f"Loan request for **{st.session_state.vendor_name}** of **₹{st.session_state.loan_amount:.2f}** has been submitted.")
    st.info("(In a real scenario, this would go through an approval process. For this demo, let's simulate approval.)")

    if st.session_state.business_type_input.lower() == "food" and st.session_state.food_business_increment > 0:
        st.info(f"✨ Your loan amount includes an additional ₹{st.session_state.food_business_increment:.2f} due to your 'Food' business type.")

    if st.button("Simulate Loan Approval"):
        st.session_state.app_state = 'loan_approved'
        st.session_state.message = f"Loan for {st.session_state.vendor_name} approved! Ready for disbursement."
        st.rerun()

elif st.session_state.app_state == 'loan_approved':
    st.write(f"Loan for **{st.session_state.vendor_name}** of **₹{st.session_state.loan_amount:.2f}** is approved!")

    # --- NEW: Input for Payee ID ---
    st.session_state.payee_id_input = st.text_input(
        "Enter Vendor's Payman AI Payee ID (Payment Destination ID)",
        value=st.session_state.payee_id_input,
        placeholder="e.g., payee_XXXXX_YYYYY"
    )

    if st.button("Disburse Loan via Payman AI"):
        if not st.session_state.payee_id_input:
            st.warning("Please enter the Vendor's Payman AI Payee ID to disburse the loan.")
            st.rerun() # Rerun to display warning
        else:
            with st.spinner("Disbursing loan..."):
                st.session_state.message = "Loan disbursement in progress..."
                payment_result = send_payman_payment(
                    st.session_state.payee_id_input, # Use the dynamically entered ID
                    st.session_state.loan_amount,
                    f"Micro-loan for {st.session_state.vendor_name}'s Thela",
                    currency="INR"
                )

                if payment_result["status"] == "success":
                    st.session_state.message = f"Loan of ₹{st.session_state.loan_amount:.2f} disbursed successfully! Transaction ID: {payment_result['data'].get('id', 'N/A')}"
                    st.session_state.current_balance += st.session_state.loan_amount
                    st.session_state.loan_disbursed = True
                    st.session_state.app_state = 'tracking_sales'
                else:
                    st.session_state.message = payment_result["message"]
                st.rerun()

elif st.session_state.app_state == 'tracking_sales':
    st.subheader(f"Vendor: {st.session_state.vendor_name}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Balance", f"₹{st.session_state.current_balance:.2f}")
    with col2:
        st.metric("Total Bonuses", f"₹{st.session_state.total_bonuses:.2f}")
    with col3:
        st.metric("Days Tracked", st.session_state.days_tracked)

    with st.form("daily_sales_form"):
        st.session_state.daily_sales_input = st.number_input("Enter Day's Sales (₹)", min_value=0.0, value=st.session_state.daily_sales_input, step=1.0)
        submitted_sales = st.form_submit_button("Record Sales & Check for Bonus")
        if submitted_sales:
            st.session_state.days_tracked += 1
            st.session_state.message = f"Day {st.session_state.days_tracked} sales recorded: ₹{st.session_state.daily_sales_input:.2f}. Checking for bonus..."

            if st.session_state.daily_sales_input >= 50:
                with st.spinner("Issuing growth bonus..."):
                    bonus_amount = 5.00
                    payment_result = send_payman_payment(
                        st.session_state.payee_id_input, # Use the dynamically entered ID for bonuses too
                        bonus_amount,
                        f"Growth bonus for {st.session_state.vendor_name} (sales performance)",
                        currency="INR"
                    )
                    if payment_result["status"] == "success":
                        st.session_state.message = f"Growth bonus of ₹{bonus_amount:.2f} issued! Transaction ID: {payment_result['data'].get('id', 'N/A')}"
                        st.session_state.current_balance += bonus_amount
                        st.session_state.total_bonuses += bonus_amount
                    else:
                        st.session_state.message = payment_result["message"]
            else:
                st.session_state.message = f"Day {st.session_state.days_tracked} sales recorded: ₹{st.session_state.daily_sales_input:.2f}. No bonus this time."
            st.rerun()

st.markdown("---")
st.caption("Powered by Payman AI (Direct API Calls via `requests`)")
st.caption("**Important:** For production, ensure secure handling of Payee IDs (e.g., fetching from a database) and robust error handling.")