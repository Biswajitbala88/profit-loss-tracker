from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from html import escape
import calendar

import streamlit as st

from database import (
    add_trade,
    delete_trade,
    get_daily_totals_between,
    get_monthly_earnings,
    get_monthly_totals,
    get_total_between,
    get_trades_for_day,
    init_db,
    update_trade,
)


st.set_page_config(page_title="P&L Calendar", layout="wide")


def money(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}₹{abs(value):,.2f}"


def progress_percent(earnings: Decimal, goal: Decimal) -> Decimal:
    if goal <= 0:
        return Decimal("0")
    return max(Decimal("0"), (earnings / goal) * Decimal("100"))


def inject_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg: #050608;
                --panel: #101216;
                --panel-soft: #171a20;
                --border: #2a2f38;
                --text: #f4f7fb;
                --muted: #8c95a3;
                --green: #18a957;
                --green-soft: rgba(24, 169, 87, 0.18);
                --red: #d84a4a;
                --red-soft: rgba(216, 74, 74, 0.18);
                --gold: #f0b84f;
            }

            .stApp {
                background: radial-gradient(circle at top, #121621 0, var(--bg) 42%);
                color: var(--text);
            }

            [data-testid="stHeader"] {
                background: transparent;
            }

            .block-container {
                max-width: 1180px;
                padding-top: 2rem;
                padding-bottom: 3rem;
            }

            .app-title {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 1rem;
            }

            .app-title h1 {
                color: var(--text);
                font-size: 2rem;
                line-height: 1.1;
                margin: 0;
                letter-spacing: 0;
            }

            .month-label {
                color: var(--muted);
                font-size: 0.95rem;
                margin-top: 0.2rem;
            }

            .metric-card {
                background: linear-gradient(180deg, #171a20 0%, #0f1116 100%);
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 1.15rem 1.2rem;
                min-height: 118px;
                box-shadow: 0 18px 44px rgba(0, 0, 0, 0.28);
            }

            .metric-label {
                color: var(--muted);
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-bottom: 0.55rem;
            }

            .metric-value {
                color: var(--text);
                font-size: clamp(1.55rem, 3vw, 2.25rem);
                font-weight: 800;
                letter-spacing: 0;
            }

            .metric-value.positive { color: #35d77f; }
            .metric-value.negative { color: #ff6b6b; }

            .calendar-shell {
                margin-top: 1.35rem;
                background: #090b0f;
                border: 1px solid var(--border);
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 24px 70px rgba(0, 0, 0, 0.36);
            }

            .weekday-grid,
            .calendar-grid {
                display: grid;
                grid-template-columns: repeat(7, minmax(0, 1fr));
            }

            .weekday {
                background: #11141a;
                border-right: 1px solid var(--border);
                color: var(--muted);
                font-size: 0.74rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                padding: 0.75rem 0.6rem;
                text-align: center;
                text-transform: uppercase;
            }

            .weekday:last-child { border-right: 0; }

            .day-cell {
                min-height: 118px;
                background: var(--panel);
                border-top: 1px solid var(--border);
                border-right: 1px solid var(--border);
                padding: 0.72rem;
                position: relative;
            }

            .day-link {
                color: inherit;
                display: block;
                text-decoration: none;
            }

            .day-link:hover .day-cell {
                border-color: var(--gold);
                box-shadow: inset 0 0 0 1px var(--gold);
            }

            .day-link:nth-child(7n) .day-cell,
            .day-cell:nth-child(7n) {
                border-right: 0;
            }

            .day-cell.empty {
                background:
                    repeating-linear-gradient(
                        135deg,
                        #0b0d11,
                        #0b0d11 8px,
                        #0e1015 8px,
                        #0e1015 16px
                    );
            }

            .day-cell.profit {
                background: linear-gradient(180deg, rgba(24, 169, 87, 0.92), rgba(19, 125, 68, 0.92));
            }

            .day-cell.loss {
                background: linear-gradient(180deg, rgba(216, 74, 74, 0.94), rgba(157, 42, 48, 0.94));
            }

            .day-number {
                color: var(--text);
                font-size: 0.9rem;
                font-weight: 800;
            }

            .day-amount {
                color: var(--text);
                font-size: clamp(1rem, 1.8vw, 1.45rem);
                font-weight: 900;
                margin-top: 1.55rem;
                text-align: center;
                word-break: break-word;
            }

            .day-note {
                bottom: 0.55rem;
                color: rgba(255, 255, 255, 0.76);
                font-size: 0.72rem;
                left: 0.72rem;
                position: absolute;
                right: 0.72rem;
                text-align: center;
            }

            .yearly-shell {
                margin-top: 1.6rem;
                background: #090b0f;
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 1rem;
                overflow-x: auto;
                box-shadow: 0 18px 48px rgba(0, 0, 0, 0.28);
            }

            .yearly-header {
                align-items: start;
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 0.9rem;
            }

            .yearly-title {
                color: var(--text);
                font-size: 1.05rem;
                font-weight: 800;
                letter-spacing: 0;
                margin: 0;
            }

            .yearly-subtitle {
                color: var(--muted);
                font-size: 0.82rem;
                margin-top: 0.25rem;
            }

            .yearly-legend {
                align-items: center;
                color: var(--muted);
                display: flex;
                flex-wrap: wrap;
                font-size: 0.72rem;
                gap: 0.32rem;
                justify-content: flex-end;
                min-width: 210px;
            }

            .yearly-grid-wrap {
                display: inline-grid;
                grid-template-columns: 28px auto;
                grid-template-rows: 18px auto;
                gap: 0.35rem 0.45rem;
                min-width: 820px;
            }

            .month-row {
                display: grid;
                grid-template-columns: repeat(var(--weeks), 13px);
                grid-column: 2;
                grid-row: 1;
                gap: 3px;
            }

            .month-marker {
                color: var(--muted);
                font-size: 0.68rem;
                line-height: 1;
            }

            .weekday-column {
                display: grid;
                grid-template-rows: repeat(7, 13px);
                gap: 3px;
                grid-column: 1;
                grid-row: 2;
            }

            .heatmap-grid {
                display: grid;
                grid-template-columns: repeat(var(--weeks), 13px);
                grid-template-rows: repeat(7, 13px);
                gap: 3px;
                grid-column: 2;
                grid-row: 2;
                grid-auto-flow: column;
            }

            .weekday-tick {
                color: var(--muted);
                font-size: 0.64rem;
                line-height: 13px;
                text-align: right;
            }

            .heat-day,
            .legend-swatch {
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 3px;
                display: block;
                height: 13px;
                width: 13px;
            }

            .heat-day.empty {
                background: transparent;
                border-color: transparent;
            }

            .heat-day.neutral,
            .legend-swatch.neutral { background: #171a20; }

            .heat-day.profit-1,
            .legend-swatch.profit-1 { background: rgba(24, 169, 87, 0.34); }

            .heat-day.profit-2,
            .legend-swatch.profit-2 { background: rgba(24, 169, 87, 0.58); }

            .heat-day.profit-3,
            .legend-swatch.profit-3 { background: rgba(24, 169, 87, 0.82); }

            .heat-day.loss-1,
            .legend-swatch.loss-1 { background: rgba(216, 74, 74, 0.36); }

            .heat-day.loss-2,
            .legend-swatch.loss-2 { background: rgba(216, 74, 74, 0.62); }

            .heat-day.loss-3,
            .legend-swatch.loss-3 { background: rgba(216, 74, 74, 0.88); }

            .yearly-summary {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.65rem;
                margin-top: 1rem;
            }

            .summary-item {
                background: #101216;
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 0.7rem 0.8rem;
            }

            .summary-label {
                color: var(--muted);
                font-size: 0.68rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .summary-value {
                color: var(--text);
                font-size: 1rem;
                font-weight: 800;
                margin-top: 0.2rem;
            }

            div[data-testid="stButton"] > button {
                background: #171a20;
                border: 1px solid var(--border);
                border-radius: 8px;
                color: var(--text);
                font-weight: 700;
                min-height: 2.55rem;
            }

            div[data-testid="stButton"] > button:hover {
                border-color: var(--gold);
                color: var(--gold);
            }

            div[data-testid="stForm"] {
                background: #0d1015;
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 1rem;
            }

            .stNumberInput input,
            .stTextInput input,
            .stDateInput input,
            .stSelectbox div[data-baseweb="select"] {
                background: #11141a;
                color: var(--text);
            }

            @media (max-width: 760px) {
                .day-cell {
                    min-height: 92px;
                    padding: 0.5rem;
                }

                .day-amount {
                    margin-top: 1rem;
                    font-size: 0.85rem;
                }

                .weekday {
                    font-size: 0.62rem;
                    padding: 0.55rem 0.25rem;
                }

                .yearly-header,
                .yearly-summary {
                    grid-template-columns: 1fr;
                }

                .yearly-header {
                    display: grid;
                }

                .yearly-legend {
                    justify-content: flex-start;
                    min-width: 0;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label: str, value: str, tone: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value {tone}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def amount_tone(value: Decimal) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return ""


def render_day_cell(day_number: int, total: Decimal | None, selected_year: int, selected_month: int) -> str:
    if day_number == 0:
        return '<div class="day-cell empty"></div>'

    css_class = "profit" if total and total > 0 else "loss" if total and total < 0 else ""
    amount_html = f'<div class="day-amount">{money(total)}</div>' if total else ""
    note = "Profit" if total and total > 0 else "Loss" if total and total < 0 else "No trades"
    cell_date = date(selected_year, selected_month, day_number)
    href = (
        f"?selected_date={cell_date.isoformat()}"
        f"&month={selected_month}"
        f"&year={selected_year}"
        "&show_form=1"
    )
    return (
        f'<a class="day-link" href="{href}" target="_self">'
        f'<div class="day-cell {css_class}">'
        f'<div class="day-number">{day_number}</div>'
        f"{amount_html}"
        f'<div class="day-note">{escape(note)}</div>'
        "</div>"
        "</a>"
    )


def heatmap_class(total: Decimal | None, max_profit: Decimal, max_loss: Decimal) -> str:
    if total is None or total == 0:
        return "neutral"

    if total > 0:
        intensity = total / max_profit if max_profit else Decimal("0")
        if intensity >= Decimal("0.67"):
            return "profit-3"
        if intensity >= Decimal("0.34"):
            return "profit-2"
        return "profit-1"

    intensity = abs(total) / max_loss if max_loss else Decimal("0")
    if intensity >= Decimal("0.67"):
        return "loss-3"
    if intensity >= Decimal("0.34"):
        return "loss-2"
    return "loss-1"


def render_yearly_heatmap(today: date) -> None:
    start_date = today - timedelta(days=364)
    first_grid_day = start_date - timedelta(days=(start_date.weekday() + 1) % 7)
    last_grid_day = today + timedelta(days=(5 - today.weekday()) % 7)
    total_days = (last_grid_day - first_grid_day).days + 1
    total_weeks = total_days // 7
    daily_totals = get_daily_totals_between(start_date, today)

    positive_totals = [total for total in daily_totals.values() if total > 0]
    negative_totals = [abs(total) for total in daily_totals.values() if total < 0]
    max_profit = max(positive_totals, default=Decimal("0"))
    max_loss = max(negative_totals, default=Decimal("0"))
    active_days = len(daily_totals)
    profitable_days = sum(1 for total in daily_totals.values() if total > 0)
    losing_days = sum(1 for total in daily_totals.values() if total < 0)
    consistency = (Decimal(active_days) / Decimal("365")) * Decimal("100")

    month_cells: list[str] = []
    previous_month = None
    for week_index in range(total_weeks):
        week_start = first_grid_day + timedelta(days=week_index * 7)
        label = ""
        if start_date <= week_start <= today and week_start.month != previous_month:
            label = calendar.month_abbr[week_start.month]
            previous_month = week_start.month
        month_cells.append(f'<div class="month-marker">{escape(label)}</div>')

    day_cells: list[str] = []
    for week_index in range(total_weeks):
        for weekday_index in range(7):
            current_day = first_grid_day + timedelta(days=week_index * 7 + weekday_index)
            if current_day < start_date or current_day > today:
                day_cells.append('<span class="heat-day empty"></span>')
                continue

            total = daily_totals.get(current_day)
            css_class = heatmap_class(total, max_profit, max_loss)
            title_amount = money(total) if total is not None else "No trades"
            title = f"{current_day:%b %d, %Y}: {title_amount}"
            day_cells.append(f'<span class="heat-day {css_class}" title="{escape(title)}"></span>')

    html = f"""
        <div class="yearly-shell">
            <div class="yearly-header">
                <div>
                    <div class="yearly-title">Yearly View</div>
                    <div class="yearly-subtitle">Trading consistency over the last 12 months</div>
                </div>
                <div class="yearly-legend">
                    <span>Loss</span>
                    <span class="legend-swatch loss-3"></span>
                    <span class="legend-swatch loss-2"></span>
                    <span class="legend-swatch loss-1"></span>
                    <span class="legend-swatch neutral"></span>
                    <span class="legend-swatch profit-1"></span>
                    <span class="legend-swatch profit-2"></span>
                    <span class="legend-swatch profit-3"></span>
                    <span>Profit</span>
                </div>
            </div>
            <div class="yearly-grid-wrap" style="--weeks: {total_weeks};">
                <div class="month-row">{''.join(month_cells)}</div>
                <div class="weekday-column">
                    <div class="weekday-tick"></div>
                    <div class="weekday-tick">Mon</div>
                    <div class="weekday-tick"></div>
                    <div class="weekday-tick">Wed</div>
                    <div class="weekday-tick"></div>
                    <div class="weekday-tick">Fri</div>
                    <div class="weekday-tick"></div>
                </div>
                <div class="heatmap-grid">{''.join(day_cells)}</div>
            </div>
            <div class="yearly-summary">
                <div class="summary-item">
                    <div class="summary-label">Active Days</div>
                    <div class="summary-value">{active_days} / 365</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Consistency</div>
                    <div class="summary-value">{consistency:.1f}%</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Win / Loss Days</div>
                    <div class="summary-value">{profitable_days} / {losing_days}</div>
                </div>
            </div>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def open_trade_form(trade_date: date) -> None:
    st.session_state.selected_date = trade_date
    st.session_state.show_form = True


def close_trade_form() -> None:
    st.session_state.show_form = False
    st.query_params["show_form"] = "0"


def render_edit_trades(selected_date: date) -> None:
    trades = get_trades_for_day(selected_date)

    if not trades:
        st.caption("No trades recorded for this day yet.")
        return

    st.markdown("**Edit trades for selected day**")
    st.caption(f"{selected_date:%b %d, %Y}")
    for trade in trades:
        with st.form(f"edit_trade_{trade.id}"):
            st.markdown(f"**Trade #{trade.id}**")
            edit_cols = st.columns([1, 1, 2])
            with edit_cols[0]:
                edited_date = st.date_input("Date", value=trade.date, key=f"date_{trade.id}")
            with edit_cols[1]:
                edited_amount = st.number_input(
                    "Amount",
                    value=float(trade.amount),
                    step=25.0,
                    format="%.2f",
                    key=f"amount_{trade.id}",
                )
            with edit_cols[2]:
                edited_note = st.text_input(
                    "Note",
                    value=trade.note,
                    placeholder="Optional context",
                    key=f"note_{trade.id}",
                )

            action_cols = st.columns(2)
            with action_cols[0]:
                update_submitted = st.form_submit_button("Update", use_container_width=True)
            with action_cols[1]:
                delete_submitted = st.form_submit_button("Delete", use_container_width=True)

        if update_submitted:
            try:
                parsed_amount = Decimal(str(edited_amount))
                if parsed_amount == 0:
                    st.warning("Enter a non-zero trade amount.")
                    return
                updated = update_trade(trade.id, edited_date, parsed_amount, edited_note)
            except (InvalidOperation, ValueError) as exc:
                st.error(f"Could not update trade: {exc}")
                return
            except Exception as exc:
                st.error(f"Database error: {exc}")
                return

            if updated is None:
                st.error("That trade no longer exists.")
                return
            st.success("Trade updated.")
            st.rerun()

        if delete_submitted:
            try:
                deleted = delete_trade(trade.id)
            except Exception as exc:
                st.error(f"Database error: {exc}")
                return

            if not deleted:
                st.error("That trade no longer exists.")
                return
            st.success("Trade deleted.")
            st.rerun()


@st.dialog("Add / Edit Trade", width="large", on_dismiss=close_trade_form)
def render_trade_form() -> None:
    selected_date = st.session_state.get("selected_date", date.today())
    st.subheader(f"Add Trade - {selected_date:%b %d, %Y}")

    with st.form("trade_form", clear_on_submit=True):
        trade_date = st.date_input("Date", value=selected_date)
        amount = st.number_input("Amount", value=0.0, step=25.0, format="%.2f")
        note = st.text_input("Note", placeholder="Optional context")
        submitted = st.form_submit_button("Save Trade", use_container_width=True)

    if submitted:
        try:
            parsed_amount = Decimal(str(amount))
            if parsed_amount == 0:
                st.warning("Enter a non-zero trade amount.")
                return
            add_trade(trade_date, parsed_amount, note)
        except (InvalidOperation, ValueError) as exc:
            st.error(f"Could not save trade: {exc}")
            return
        except Exception as exc:  # Streamlit should surface database issues without crashing the page.
            st.error(f"Database error: {exc}")
            return

        st.success("Trade saved.")
        st.rerun()

    st.divider()
    render_edit_trades(selected_date)

    if st.button("Close", use_container_width=True):
        close_trade_form()
        st.rerun()


def main() -> None:
    init_db()
    inject_css()

    today = date.today()
    query_params = st.query_params
    query_date = query_params.get("selected_date")
    query_month = query_params.get("month")
    query_year = query_params.get("year")

    default_date = today
    if query_date:
        try:
            default_date = date.fromisoformat(query_date)
        except ValueError:
            default_date = today

    if "selected_date" not in st.session_state:
        st.session_state.selected_date = default_date
    elif query_date:
        st.session_state.selected_date = default_date

    if "show_form" not in st.session_state:
        st.session_state.show_form = query_params.get("show_form") == "1"
    elif query_params.get("show_form") == "1":
        st.session_state.show_form = True

    st.markdown(
        """
        <div class="app-title">
            <div>
                <h1>Profit and Loss Calendar</h1>
                <div class="month-label">Track daily trading P&amp;L against your monthly goal.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    controls = st.columns([1, 1, 1])
    try:
        default_month = int(query_month or today.month)
    except ValueError:
        default_month = today.month
    default_month = min(12, max(1, default_month))

    try:
        default_year = int(query_year or today.year)
    except ValueError:
        default_year = today.year

    with controls[0]:
        selected_month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            index=default_month - 1,
            format_func=lambda month: calendar.month_name[month],
        )
    with controls[1]:
        selected_year = st.number_input("Year", value=default_year, min_value=2000, max_value=2100, step=1)
    with controls[2]:
        monthly_goal = Decimal(
            str(st.number_input("Monthly Goal", value=5000.0, min_value=0.0, step=500.0, format="%.2f"))
        )

    selected_year = int(selected_year)
    monthly_totals = get_monthly_totals(selected_year, selected_month)
    monthly_earnings = get_monthly_earnings(selected_year, selected_month)
    year_to_date_total = get_total_between(date(today.year, 1, 1), today)
    progress = progress_percent(monthly_earnings, monthly_goal)

    metric_cols = st.columns(4)
    with metric_cols[0]:
        render_metric(
            "Monthly Earnings",
            money(monthly_earnings),
            amount_tone(monthly_earnings),
        )
    with metric_cols[1]:
        render_metric("Progress %", f"{progress:.1f}%")
    with metric_cols[2]:
        render_metric("Monthly Goal", money(monthly_goal))
    with metric_cols[3]:
        render_metric(
            "Jan 1 - Today P&L",
            money(year_to_date_total),
            amount_tone(year_to_date_total),
        )

    month_matrix = calendar.Calendar(firstweekday=6).monthdayscalendar(selected_year, selected_month)
    calendar_html = (
        '<div class="calendar-shell">'
        '<div class="weekday-grid">'
        + "".join(f'<div class="weekday">{day}</div>' for day in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
        + "</div>"
        '<div class="calendar-grid">'
    )
    for week in month_matrix:
        for day_number in week:
            cell_date = date(selected_year, selected_month, day_number) if day_number else None
            calendar_html += render_day_cell(
                day_number,
                monthly_totals.get(cell_date) if cell_date else None,
                selected_year,
                selected_month,
            )

    calendar_html += "</div></div>"
    st.markdown(calendar_html, unsafe_allow_html=True)
    render_yearly_heatmap(today)

    if st.session_state.show_form:
        render_trade_form()


if __name__ == "__main__":
    main()
