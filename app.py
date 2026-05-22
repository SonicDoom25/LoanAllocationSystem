# app.py
import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from banker import BankersAlgorithm
import database as db
from eligibility import check_financial_eligibility

app = Flask(__name__)
app.secret_key = "replace_this_with_a_secure_key"

# default bank reserve constant (used only if DB empty)
DEFAULT_BANK_RESERVE = 500000


# -------------------------------
# Home
# -------------------------------
@app.route("/")
def home():
    reserve = db.get_bank_reserve()
    return render_template(
        "home.html",
        bank_reserve=reserve,
        bank_reserve_default=DEFAULT_BANK_RESERVE
    )


# -------------------------------
# Loan Application Page
# -------------------------------
@app.route("/apply", methods=["GET"])
def loan_application():
    return render_template("loan_application.html")


# -------------------------------
# API endpoint: Analyze & Allocate Immediately (AJAX)
# -------------------------------
@app.route("/api/apply", methods=["POST"])
def api_apply():
    """
    Expects JSON body (AJAX). Runs Banker + Eligibility and returns JSON.
    """
    try:
        data = request.json
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        address = data.get("address", "").strip()
        amount = int(data.get("amount", 0) or 0)
        tenure = int(data.get("tenure", 0) or 0)
        gender = data.get("gender", "Male")
        loan_type = data.get("loanType", "Personal Loan")
        employment = data.get("employment", "Salaried")
        income = int(data.get("income", 0) or 0)
    except Exception as e:
        return jsonify({"ok": False, "error": "Invalid input", "detail": str(e)}), 400

    if not name or not email or amount <= 0 or income <= 0 or tenure <= 0:
        return jsonify({"ok": False, "error": "Please fill required fields (name,email,amount,income,tenure)."}), 400

    # Gather existing approved loans to calculate total allocation
    loans = db.get_all_requests()
    total_allocated = sum(int(l.get("approvedAmount", 0) or 0) for l in loans)

    # Build Banker's matrices
    allocations = [[int(l.get("approvedAmount", 0) or 0)] for l in reversed(loans)]
    max_demands = [[int(l.get("requestedAmount", 0) or 0)] for l in reversed(loans)]

    # Add new applicant as a new process
    allocations.append([0])
    max_demands.append([amount])

    bank_available = db.get_bank_reserve() - total_allocated
    if bank_available < 0:
        bank_available = 0

    available_vector = [bank_available]

    # Run Banker's Algorithm
    ba = BankersAlgorithm(allocations, max_demands, available_vector)
    res = ba.get_result()

    # Financial eligibility check
    eligible, eligibility_msg = check_financial_eligibility(income, amount, tenure)

    # Decide approval
    if res["safe"] and eligible and amount <= db.get_bank_reserve():
        approved_amount = amount
        status = "Approved"
        message = f"{res['message']} | {eligibility_msg} | Loan Approved"
    elif not res["safe"]:
        approved_amount = 0
        status = "Rejected"
        message = f"{res['message']} | Loan Rejected (unsafe system)"
    else:
        approved_amount = 0
        status = "Rejected"
        message = f"{eligibility_msg} | Loan Rejected (ineligible or insufficient reserve)"

    # Persist request
    new_id = db.insert_loan_request_record(
        processes=1,
        resources=1,
        allocation=[[0]],
        maximum=[[amount]],
        available=[bank_available],
        applicantName=name,
        email=email,
        requestedAmount=amount,
        approvedAmount=approved_amount,
        income=income,
        months=tenure,
        status=status
    )

    # Adjust reserve if approved
    if approved_amount > 0:
        db.adjust_bank_reserve(approved_amount)

    current_reserve = db.get_bank_reserve()

    resp = {
        "ok": True,
        "id": new_id,
        "status": status,
        "approvedAmount": approved_amount,
        "safe": res["safe"],
        "sequence": res["sequence"],
        "message": message,
        "bank_reserve_after": current_reserve,
        "chart": {
            "allocations": allocations,
            "max": max_demands,
            "available": available_vector
        }
    }
    return jsonify(resp)


# -------------------------------
# Reserve Status (for Progress Bar)
# -------------------------------
@app.route("/reserve/status", methods=["GET"])
def reserve_status():
    reserve = db.get_bank_reserve()
    default = DEFAULT_BANK_RESERVE
    pct = int((reserve / default) * 100) if default > 0 else 0
    return jsonify({"reserve": reserve, "default": default, "percent": pct})


# -------------------------------
# Reset Reserve (Button or Manual)
# -------------------------------
@app.route("/reserve_reset", methods=["POST"])
def reserve_reset():
    db.reset_bank_reserve_to_default()
    flash("Bank reserve reset successfully.")
    return redirect(url_for("home"))


# -------------------------------
# Analysis Page
# -------------------------------
@app.route("/analysis")
def analysis():
    loans = db.fetch_all_requests()
    if not loans:
        flash("No loan data available for analysis yet.")
        return redirect(url_for("home"))

    incomes = [int(ln.get("income", 0) or 0) for ln in loans]
    requested = [int(ln.get("requestedAmount", 0) or 0) for ln in loans]
    approved = [int(ln.get("approvedAmount", 0) or 0) for ln in loans]
    statuses = [ln.get("status", "Pending") for ln in loans]
    applicants = [ln.get("applicantName", "-") for ln in loans]

    last = loans[-1]
    alloc = last.get("allocation") or []
    maxm = last.get("max") or []
    avail = last.get("available") or []

    return render_template(
        "analysis.html",
        loans=loans,
        incomes=incomes,
        requested=requested,
        approved=approved,
        statuses=statuses,
        applicants=applicants,
        allocation=alloc,
        maximum=maxm,
        available=avail,
        bank_reserve=db.get_bank_reserve(),
        bank_default=DEFAULT_BANK_RESERVE
    )


# -------------------------------
# Loan Requests (History)
# -------------------------------
@app.route("/requests")
def requests_page():
    rows = db.get_all_requests()
    reserve = db.get_bank_reserve()
    return render_template("loan_requests.html", requests=rows, bank_reserve=reserve)


# -------------------------------
# View single request (needed by loan_requests.html)
# -------------------------------
@app.route("/request/<int:id_>")
def view_request(id_):
    r = db.get_request_by_id(id_)
    if not r:
        flash("Request not found.")
        return redirect(url_for("requests_page"))
    reserve = db.get_bank_reserve()
    return render_template("view_request.html", r=r, bank_reserve=reserve, bank_reserve_default=DEFAULT_BANK_RESERVE)


# -------------------------------
# Edit request (simple: update key fields)
# -------------------------------
@app.route("/request/<int:id_>/edit", methods=["GET", "POST"])
def edit_request(id_):
    r = db.get_request_by_id(id_)
    if not r:
        flash("Request not found.")
        return redirect(url_for("requests_page"))

    if request.method == "POST":
        # Accept edits for a few fields from form
        applicantName = request.form.get("applicantName", r.get("applicantName"))
        email = request.form.get("email", r.get("email"))
        requestedAmount = int(request.form.get("requestedAmount", r.get("requestedAmount", 0) or 0))
        approvedAmount = int(request.form.get("approvedAmount", r.get("approvedAmount", 0) or 0))
        income = int(request.form.get("income", r.get("income", 0) or 0))
        months = int(request.form.get("months", r.get("months", 12) or 12))
        status = request.form.get("status", r.get("status", "Pending"))

        # update via SQL directly (small helper)
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE loan_requests
            SET applicantName=?, email=?, requestedAmount=?, approvedAmount=?, income=?, months=?, status=?
            WHERE id=?
        """, (applicantName, email, requestedAmount, approvedAmount, income, months, status, id_))
        conn.commit()
        conn.close()

        # If approvedAmount changed and >0, ensure reserve updated accordingly.
        # (This is a simple approach: we will NOT auto-adjust reserve here to avoid double-subtracting;
        #  prefer managing reserve via allocation flow.)
        flash("Request updated.")
        return redirect(url_for("view_request", id_=id_))

    # GET: show edit form
    reserve = db.get_bank_reserve()
    return render_template("edit_request.html", r=r, bank_reserve=reserve, bank_reserve_default=DEFAULT_BANK_RESERVE)


# -------------------------------
# Delete single request
# -------------------------------
@app.route("/request/<int:id_>/delete", methods=["POST"])
def delete_request(id_):
    db.delete_request_by_id(id_)
    flash("Deleted.")
    return redirect(url_for("requests_page"))


# -------------------------------
# Delete All Requests + Reset Reserve
# -------------------------------
@app.route("/requests/delete_all", methods=["POST"])
def delete_all():
    db.delete_all_requests()
    db.reset_bank_reserve_to_default()
    flash("All loan records deleted and bank reserve reset.")
    return redirect(url_for("requests_page"))


# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
