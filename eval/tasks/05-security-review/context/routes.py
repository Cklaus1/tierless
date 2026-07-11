"""Invoice API for a multi-tenant B2B app. Each user belongs to one organization.
Under review before merge. Auth is handled by @require_auth, which sets
request.user (with .id and .org_id) from a validated session token."""

from flask import request, jsonify, abort
from app.db import db
from app.models import Invoice, Organization
from app.auth import require_auth


@app.route("/api/invoices/<int:invoice_id>", methods=["GET"])
@require_auth
def get_invoice(invoice_id):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        abort(404)
    return jsonify(invoice.to_dict())


@app.route("/api/invoices", methods=["POST"])
@require_auth
def create_invoice():
    data = request.get_json()
    invoice = Invoice(
        org_id=request.user.org_id,
        amount_cents=data["amount_cents"],
        customer_name=data["customer_name"],
    )
    db.add(invoice)
    db.commit()
    return jsonify(invoice.to_dict()), 201


@app.route("/api/invoices/<int:invoice_id>", methods=["DELETE"])
@require_auth
def delete_invoice(invoice_id):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        abort(404)
    db.delete(invoice)
    db.commit()
    return "", 204


@app.route("/api/orgs/<int:org_id>/report", methods=["GET"])
@require_auth
def org_report(org_id):
    # returns aggregate revenue for the org
    total = db.query(db.func.sum(Invoice.amount_cents)).filter(
        Invoice.org_id == org_id
    ).scalar()
    return jsonify({"org_id": org_id, "total_cents": total or 0})
