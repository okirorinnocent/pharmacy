class MicroCreditEngine:
    """Evaluates drug shop repayment history to grant 7-day trade credit limits."""

    @staticmethod
    def calculate_credit_limit(total_completed_orders: int, avg_order_value_ugx: float, repayment_score: float) -> float:
        """
        repayment_score ranges from 0.0 to 1.0 (on-time payments ratio).
        Requires minimum 3 completed orders before extending trade credit.
        """
        if total_completed_orders < 3 or repayment_score < 0.8:
            return 0.0

        # Max credit limit is capped at 50% of average monthly purchase volume
        multiplier = 0.3 if total_completed_orders < 10 else 0.5
        calculated_limit = avg_order_value_ugx * multiplier * repayment_score

        # Cap initial credit at UGX 2,000,000 ($540 USD) for risk control
        return min(calculated_limit, 2000000.0)


credit_engine = MicroCreditEngine()
