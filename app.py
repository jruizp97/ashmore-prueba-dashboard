import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import dash_bootstrap_components as dbc

# =========================
# INITIALIZE APP
# =========================

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY]
)

# =========================
# LOAD DATA
# =========================

budget = pd.read_csv(
    "Budget_Clean.csv",
    sep=";",
    encoding="latin1"
)

pnl = pd.read_csv(
    "Pnl_Clean.csv",
    sep=";",
    encoding="latin1"
)

# =========================
# CLEAN COLUMNS
# =========================

budget = budget.loc[:, ~budget.columns.str.contains("^Unnamed")]
pnl = pnl.loc[:, ~pnl.columns.str.contains("^Unnamed")]

# =========================
# FIX DATES
# =========================

budget["Month_Date"] = pd.to_datetime(
    budget["Month_Date"],
    dayfirst=True
).dt.to_period("M").dt.to_timestamp()

pnl["Month_Date"] = pd.to_datetime(
    pnl["Month_Date"],
    dayfirst=True
).dt.to_period("M").dt.to_timestamp()

# =========================
# STANDARDIZE BUDGET TABLE
# =========================

budget_fact = budget[[
    "Month_Date",
    "Month_Label",
    "Category",
    "Account Name",
    "Budget_COP",
    "Budget_GBP"
]].copy()

budget_fact["Scenario"] = "Budget"

budget_fact.rename(columns={
    "Account Name": "Account",
    "Budget_COP": "Amount_COP",
    "Budget_GBP": "Amount_GBP"
}, inplace=True)

budget_fact["Account"] = (
    budget_fact["Account"]
    .astype(str)
    .str.strip()
)

# =========================
# STANDARDIZE PNL TABLE
# =========================

pnl_fact = pnl[[
    "Month_Date",
    "Month_Label",
    "Description",
    "Actual_COP",
    "Actual_GBP"
]].copy()

pnl_fact["Scenario"] = "Actual"

pnl_fact.rename(columns={
    "Description": "Account",
    "Actual_COP": "Amount_COP",
    "Actual_GBP": "Amount_GBP"
}, inplace=True)

pnl_fact["Category"] = "Actuals"

pnl_fact["Account"] = (
    pnl_fact["Account"]
    .astype(str)
    .str.strip()
)

# =========================
# COMBINE TABLES
# =========================

finance = pd.concat(
    [budget_fact, pnl_fact],
    ignore_index=True
)

months = sorted(finance["Month_Date"].unique())

# =========================
# APP LAYOUT
# =========================

app.layout = dbc.Container([

    html.Br(),

    html.H1(
        "Ashmore Private Equity Dashboard",
        className="text-center"
    ),

    html.H5(
        "FY26 Financial Performance",
        className="text-center text-muted"
    ),

    html.Br(),

    dbc.Row([

        dbc.Col([

            html.Label("Select Currency"),

            dcc.Dropdown(
                id="currency-selector",
                options=[
                    {"label": "COP", "value": "COP"},
                    {"label": "GBP", "value": "GBP"}
                ],
                value="COP",
                clearable=False,
                style={"color": "black"}
            )

        ], width=3),

        dbc.Col([

            html.Label("Select Month"),

            dcc.Dropdown(
                id="month-selector",
                options=[
                    {
                        "label": m.strftime("%b-%y"),
                        "value": m.strftime("%Y-%m-%d")
                    }
                    for m in months
                ],
                value=months[-1].strftime("%Y-%m-%d"),
                clearable=False,
                style={"color": "black"}
            )

        ], width=3)

    ]),

    html.Br(),

    dbc.Row([

        dbc.Col([

            html.Label("Select Account"),

            dcc.Dropdown(
                id="account-selector",
                options=[
                    {"label": "All Accounts", "value": "ALL"}
                ] + [
                    {
                        "label": acc,
                        "value": acc
                    }
                    for acc in sorted(
                        finance["Account"]
                        .dropna()
                        .unique()
                    )
                ],
                value="ALL",
                clearable=False,
                style={"color": "black"}
            )

        ], width=6)

    ]),

    html.Br(),

    dbc.Row(id="kpi-cards"),

    html.Br(),

    dbc.Row([

        dbc.Col([
            dcc.Graph(id="trend-chart")
        ])

    ]),

    html.Br(),

    dbc.Row([

        dbc.Col([
            dcc.Graph(id="variance-chart")
        ])

    ])

], fluid=True)

# =========================
# CALLBACK
# =========================

@app.callback(
    [
        Output("kpi-cards", "children"),
        Output("trend-chart", "figure"),
        Output("variance-chart", "figure")
    ],

    [
        Input("currency-selector", "value"),
        Input("month-selector", "value"),
        Input("account-selector", "value")
    ]
)

def update_dashboard(
    currency,
    selected_month,
    selected_account
):

    selected_month = pd.to_datetime(selected_month)

    metric_col = (
        "Amount_COP"
        if currency == "COP"
        else "Amount_GBP"
    )

    # =========================
    # FILTER DATA
    # =========================

    mtd_data = finance[
        finance["Month_Date"] == selected_month
    ]

    ytd_data = finance[
        finance["Month_Date"] <= selected_month
    ]

    if selected_account != "ALL":

        mtd_data = mtd_data[
            mtd_data["Account"] == selected_account
        ]

        ytd_data = ytd_data[
            ytd_data["Account"] == selected_account
        ]

    # =========================
    # KPI CALCULATIONS
    # =========================

    mtd_budget = mtd_data.loc[
        mtd_data["Scenario"] == "Budget",
        metric_col
    ].sum()

    mtd_actual = mtd_data.loc[
        mtd_data["Scenario"] == "Actual",
        metric_col
    ].sum()

    mtd_variance = mtd_actual - mtd_budget

    ytd_budget = ytd_data.loc[
        ytd_data["Scenario"] == "Budget",
        metric_col
    ].sum()

    ytd_actual = ytd_data.loc[
        ytd_data["Scenario"] == "Actual",
        metric_col
    ].sum()

    ytd_variance = ytd_actual - ytd_budget

    fy_budget = finance.loc[
        finance["Scenario"] == "Budget",
        metric_col
    ].sum()

    fy_execution = (
    abs(ytd_actual) / abs(fy_budget) * 100
        if fy_budget != 0 else 0
    )

    # =========================
    # FORMAT FUNCTION
    # =========================

    def format_value(value, currency):

        value = abs(value)

        if currency == "COP":
            return f"{value/1e9:.1f}B"

        else:

            if value >= 1e6:
                return f"{value/1e6:.1f}M"

            return f"{value/1e3:.1f}K"

    # =========================
    # KPI CARDS
    # =========================

    cards = [

        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "YTD Budget",
                        className="text-muted"
                    ),
                    html.H2(
                        format_value(ytd_budget, currency),
                        className="fw-bold"
                    )
                ]),
                className="shadow-sm border-0",
                style={
                    "borderRadius": "16px",
                    "backgroundColor": "#1a1a1a",
                    "padding": "10px"
                }
            ),
            width=2
        ),

        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "YTD Actual",
                        className="text-muted"
                    ),
                    html.H2(
                        format_value(ytd_actual, currency),
                        className="fw-bold"
                    )
                ]),
                className="shadow-sm border-0",
                style={
                    "borderRadius": "16px",
                    "backgroundColor": "#1a1a1a",
                    "padding": "10px"
                }
            ),
            width=2
        ),

        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "YTD Variance",
                        className="text-muted"
                    ),
                    html.H2(
                        format_value(ytd_variance, currency),
                        className="fw-bold"
                    )
                ]),
                className="shadow-sm border-0",
                style={
                    "borderRadius": "16px",
                    "backgroundColor": "#1a1a1a",
                    "padding": "10px"
                }
            ),
            width=2
        ),

        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "FY Execution",
                        className="text-muted"
                    ),
                    html.H2(
                        f"{fy_execution:.1f}%",
                        className="fw-bold"
                    )
                ]),
                className="shadow-sm border-0",
                style={
                    "borderRadius": "16px",
                    "backgroundColor": "#1a1a1a",
                    "padding": "10px"
                }
            ),
            width=2
        ),

        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H6(
                        "MTD Variance",
                        className="text-muted"
                    ),
                    html.H2(
                        format_value(mtd_variance, currency),
                        className="fw-bold"
                    )
                ]),
                className="shadow-sm border-0",
                style={
                    "borderRadius": "16px",
                    "backgroundColor": "#1a1a1a",
                    "padding": "10px"
                }
            ),
            width=2
        )

    ]

    # =========================
    # TREND CHART
    # =========================

    monthly_data = ytd_data.groupby(
        ["Month_Date", "Scenario"],
        as_index=False
    )[metric_col].sum()

    fig = px.line(
        monthly_data,
        x="Month_Date",
        y=metric_col,
        color="Scenario",
        markers=True,
        template="plotly_dark",
        title="Monthly Budget vs Actual Trend"
    )

    fig.update_layout(
        height=600,
        plot_bgcolor="#111111",
        paper_bgcolor="#111111",
        font=dict(
            family="Arial",
            size=14
        ),
        xaxis_title="Month",
        yaxis_title=f"Amount ({currency})"
    )

    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8)
    )

    fig.update_xaxes(
        tickformat="%b-%y",
        dtick="M1"
    )

    fig.update_yaxes(
        tickformat=",.2s"
    )

    # =========================
    # VARIANCE CHART
    # =========================

    variance_data = ytd_data.groupby(
        ["Account", "Scenario"],
        as_index=False
    )[metric_col].sum()

    variance_pivot = variance_data.pivot(
        index="Account",
        columns="Scenario",
        values=metric_col
    ).fillna(0)

    if "Actual" not in variance_pivot.columns:
        variance_pivot["Actual"] = 0

    if "Budget" not in variance_pivot.columns:
        variance_pivot["Budget"] = 0

    variance_pivot["Variance"] = (
        variance_pivot["Actual"]
        -
        variance_pivot["Budget"]
    )

    variance_pivot = variance_pivot.reindex(
        variance_pivot["Variance"]
        .abs()
        .sort_values(ascending=False)
        .index
    )

    top_variance = variance_pivot.head(10).reset_index()

    variance_fig = px.bar(
        top_variance,
        x="Variance",
        y="Account",
        orientation="h",
        color="Variance",
        color_continuous_scale="RdYlGn",
        template="plotly_dark",
        title=f"YTD Variance vs Budget by Account — through {selected_month.strftime('%b-%y')}"
    )

    variance_fig.update_layout(
        height=550,
        plot_bgcolor="#111111",
        paper_bgcolor="#111111",
        font=dict(
            family="Arial",
            size=14
        ),
        xaxis_title=f"Variance Amount ({currency})",
        yaxis_title="Account"
    )

    variance_fig.update_yaxes(
        categoryorder="total ascending"
    )

    variance_fig.update_xaxes(
        tickformat=",.2s"
    )

    return cards, fig, variance_fig

# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)

