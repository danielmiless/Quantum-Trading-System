"""Reporting utilities for analytics outputs."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable, Mapping, Optional

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


class ReportGenerator:
    """Create rich reports across multiple distribution channels."""

    def __init__(self, output_dir: str | Path = "reports") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_pdf_report(
        self,
        performance_summary: Mapping[str, float],
        time_series: Optional[pd.Series] = None,
        filename: str = "quantum_report.pdf",
    ) -> Path:
        output_path = self.output_dir / filename
        with PdfPages(output_path) as pdf:
            fig, ax = plt.subplots(figsize=(8.5, 5.5))
            ax.axis("off")
            table_data = [[k, f"{v:0.4f}"] for k, v in performance_summary.items()]
            table = ax.table(cellText=table_data, colLabels=["Metric", "Value"], loc="center")
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

            if time_series is not None and not time_series.empty:
                fig, ax = plt.subplots(figsize=(8.5, 5.5))
                time_series.cumprod().plot(ax=ax, title="Cumulative Performance")
                ax.set_ylabel("Growth of $1")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)
        return output_path

    def create_excel_report(
        self,
        sheets: Mapping[str, pd.DataFrame],
        filename: str = "quantum_report.xlsx",
    ) -> Path:
        output_path = self.output_dir / filename
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for sheet_name, df in sheets.items():
                df.to_excel(writer, sheet_name=sheet_name[:31])
        return output_path

    def create_html_dashboard(
        self,
        context: Mapping[str, object],
        filename: str = "dashboard.html",
    ) -> Path:
        output_path = self.output_dir / filename
        html = ["<html><head><title>Quantum Portfolio Dashboard</title></head><body>"]
        html.append("<h1>Quantum Portfolio Analytics</h1>")
        for key, value in context.items():
            html.append(f"<h2>{key}</h2>")
            if isinstance(value, pd.DataFrame):
                html.append(value.to_html(border=0, float_format="{:.4f}".format))
            elif isinstance(value, pd.Series):
                html.append(value.to_frame(name=key).to_html(border=0, float_format="{:.4f}".format))
            else:
                html.append(f"<p>{value}</p>")
        html.append("</body></html>")
        output_path.write_text("\n".join(html), encoding="utf-8")
        return output_path

    def send_email_report(
        self,
        smtp_server: str,
        port: int,
        sender: str,
        password: str,
        recipients: Iterable[str],
        subject: str,
        body: str,
        attachments: Optional[Iterable[Path]] = None,
        *,
        dry_run: bool = True,
    ) -> EmailMessage:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.set_content(body)

        for attachment in attachments or []:
            data = Path(attachment).read_bytes()
            message.add_attachment(
                data,
                maintype="application",
                subtype="octet-stream",
                filename=Path(attachment).name,
            )

        if not dry_run:
            with smtplib.SMTP_SSL(smtp_server, port) as server:
                server.login(sender, password)
                server.send_message(message)

        return message


__all__ = ["ReportGenerator"]

