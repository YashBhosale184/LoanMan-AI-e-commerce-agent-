def calculate_loan_amount(daily_sales: float, business_type: str, operating_days: int):
    """Calculates loan amount based on a rule-based system.

    Args:
        daily_sales: The vendor's average daily sales (float).
        business_type: The type of business (string, e.g., "food", "clothing").
        operating_days: Number of days the vendor operates in a week (int).
        # experience_years: Number of years of experience (int).
        # Note: 'experience_years' was included in args but not used in the provided logic.

    Returns:
        The recommended loan amount (float). Returns 0.0 if no loan is recommended.
    """
    base_loan_from_sales = 0.0

    #Sales-based tiers for base loan amount
    if daily_sales < 500:
        base_loan_from_sales = 0.0  # No loan for low sales
    elif daily_sales < 1000:
        base_loan_from_sales = 5000.0
    elif daily_sales < 2000:
        base_loan_from_sales = 10000.0
    else: # daily_sales >= 2000
        base_loan_from_sales = 15000.0

    #If base_loan_from_sales is 0, no need for further calculations
    if base_loan_from_sales == 0:
        return 0.0

    #Initialize adjusted loan amount with the sales-based value
    adjusted_loan_amount = base_loan_from_sales

    #Business type adjustments (applied as multipliers)
    if business_type == "food":
        adjusted_loan_amount *= 1.1 # Slightly higher for food vendors
    elif business_type == "clothing":
        adjusted_loan_amount *= 0.9 # Slightly lower for clothing
    #If business_type is 'other' or not matched, no adjustment is applied

    #Operating days bonus
    if operating_days >= 6:
        adjusted_loan_amount += 2000.0

    #Cap the loan amount to a maximum
    max_loan_amount = 20000.0
    final_loan_amount = min(adjusted_loan_amount, max_loan_amount)

    #Ensure the loan amount is at least the minimum required for practical disbursement
    min_disbursable_amount = 10.0
    if final_loan_amount < min_disbursable_amount:
        return 0.0 # Return 0.0 if the calculated loan is too small
    
    #Return as float, rounded to a whole number for cleaner loan amounts
    return float(int(final_loan_amount))

#--- Sample Usage ---
#These lines demonstrate how to call the function and print its output.
#In the Streamlit app, these values would come from user inputs.
daily_sales_sample = 1500
business_type_sample = "food"
operating_days_sample = 7
experience_years_sample = 5

loan_amount_calculated = calculate_loan_amount(daily_sales_sample, business_type_sample, operating_days_sample)

if loan_amount_calculated > 0:
    print(f"Recommended loan amount: {loan_amount_calculated}")
else:
    print("Loan not recommended based on current criteria.")
