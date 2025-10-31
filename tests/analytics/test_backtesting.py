"""Analytics and backtesting test suite."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.backtester import BacktestEngine
from analytics.benchmark_comparison import BenchmarkComparator
from analytics.monte_carlo import MonteCarloSimulator
from analytics.performance_attribution import PerformanceAnalyzer
from analytics.reporting import ReportGenerator
from analytics.risk_analytics import RiskAnalyzer, StressScenario


def create_price_data() -> pd.DataFrame:
    dates = pd.date_range("2021-01-01", periods=60, freq="B")
    assets = ["AAPL", "MSFT", "GOOGL"]
    data = {
        asset: 100 + np.cumsum(np.random.default_rng(42 + idx).normal(0, 1, len(dates)))
        for idx, asset in enumerate(assets)
    }
    return pd.DataFrame(data, index=dates)


def test_backtest_engine_basic(tmp_path) -> None:
    prices = create_price_data()
    benchmark_returns = prices["AAPL"].pct_change().fillna(0.0)
    engine = BacktestEngine(transaction_cost=0.0001, price_data=prices, benchmark_returns=benchmark_returns)
    weights = {col: 1 / len(prices.columns) for col in prices.columns}
    portfolio = {"weights": weights}
    result = engine.run_backtest(portfolio, prices.index[0], prices.index[-1], "weekly")

    assert not result.returns.empty
    assert "annualized_return" in result.metrics
    trade_turnover = result.trades["turnover"].sum()
    assert trade_turnover >= 0

    metrics = engine.calculate_performance_metrics(result.returns["portfolio"], result.returns["benchmark"])
    assert metrics["annualized_return"] == result.metrics["annualized_return"]

    signals = engine.generate_trade_signals(
        {"current_weights": {"AAPL": 0.3, "MSFT": 0.4}, "target_weights": {"AAPL": 0.4, "MSFT": 0.3}}
    )
    assert set(signals["signal"]) >= {"BUY", "SELL", "HOLD"}


def test_risk_analyzer_methods() -> None:
    analyzer = RiskAnalyzer(confidence=0.95)
    returns = pd.Series(np.random.default_rng(123).normal(0.001, 0.02, 500))
    var_hist = analyzer.value_at_risk_historical(returns)
    var_param = analyzer.value_at_risk_parametric(returns)
    var_mc = analyzer.value_at_risk_monte_carlo(returns, simulations=2000)
    es = analyzer.expected_shortfall(returns)
    max_dd, recovery = analyzer.maximum_drawdown(returns)

    assert var_hist >= 0 and var_param >= 0 and var_mc >= 0
    assert es >= 0
    assert max_dd <= 0 and recovery >= 0

    scenarios = [StressScenario("Shock", {"AAPL": -0.1, "MSFT": -0.08})]
    stress = analyzer.stress_test({"AAPL": 0.5, "MSFT": 0.5}, scenarios)
    assert not stress.empty


def test_performance_and_benchmark_analysis() -> None:
    returns = pd.Series(np.random.default_rng(99).normal(0.001, 0.01, 252))
    analyzer = PerformanceAnalyzer()
    sharpe = analyzer.calculate_sharpe_ratio(returns)
    sortino = analyzer.calculate_sortino_ratio(returns)
    calmar = analyzer.calculate_calmar_ratio(returns, max_drawdown=-0.1)
    assert np.isfinite(sharpe)
    assert np.isfinite(sortino)
    assert np.isfinite(calmar)

    comparator = BenchmarkComparator(periods_per_year=252)
    bench_returns = returns + np.random.default_rng(100).normal(0, 0.005, len(returns))
    tracking_error, info_ratio = comparator.tracking_error_and_information_ratio(returns, bench_returns)
    assert tracking_error >= 0
    active = comparator.active_share({"A": 0.5, "B": 0.5}, {"A": 0.6, "B": 0.4})
    assert 0 <= active <= 1


def test_monte_carlo_and_reporting(tmp_path) -> None:
    simulator = MonteCarloSimulator(seed=7)
    expected_returns = [0.001, 0.0015]
    cov = np.array([[0.0004, 0.0001], [0.0001, 0.0005]])
    result = simulator.simulate_portfolio_returns(expected_returns, cov, periods=10, simulations=100)
    assert "mean" in result.summary

    lower, upper = simulator.confidence_intervals(result.simulated_paths.mean(axis=1), confidence=0.9)
    assert lower <= upper

    shock_df = pd.DataFrame({"Scenario": [-0.05, -0.1]}, index=["Asset1", "Asset2"])
    losses = simulator.stress_test({"Asset1": 0.6, "Asset2": 0.4}, shock_df)
    assert not losses.empty

    generator = ReportGenerator(output_dir=tmp_path)
    pdf_path = generator.create_pdf_report(result.summary)
    excel_path = generator.create_excel_report({"Summary": pd.DataFrame([result.summary])})
    html_path = generator.create_html_dashboard({"Summary": pd.DataFrame([result.summary])})
    assert pdf_path.exists()
    assert excel_path.exists()
    assert html_path.exists()

    message = generator.send_email_report(
        smtp_server="smtp.example.com",
        port=465,
        sender="sender@example.com",
        password="password",
        recipients=["recipient@example.com"],
        subject="Quantum Report",
        body="Report attached",
        attachments=[pdf_path],
        dry_run=True,
    )
    assert "recipient@example.com" in message["To"]

