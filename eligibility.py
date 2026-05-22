# eligibility.py
def check_financial_eligibility(income, loan_amount, months, risk_type="standard"):
    """
    Checks if applicant can repay loan based on EMI-to-income ratio.
    """
    try:
        monthly_payment = loan_amount / months
        ratio = monthly_payment / income
    except ZeroDivisionError:
        return False, "❌ Invalid repayment period."
    except Exception:
        return False, "❌ Invalid data."

    # Adjust threshold by risk type
    threshold = 0.4 if risk_type == "standard" else 0.3

    if ratio <= threshold:
        return True, f"✅ Eligible (EMI {monthly_payment:.0f} ≤ {threshold*100:.0f}% of income)"
    else:
        return False, f"❌ Not eligible (EMI {monthly_payment:.0f} exceeds {threshold*100:.0f}% of income)"
