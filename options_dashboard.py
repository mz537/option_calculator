import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 底层逻辑类 
# ==========================================
class Option:
    def __init__(self, option_type, strike, premium, position='long', multiplier=1):
        self.type = option_type.lower()
        self.strike = strike
        self.premium = premium
        self.position = 1 if position.lower() == 'long' else -1
        self.multiplier = multiplier

    def calculate_payoff(self, spot_prices):
        if self.type == 'call':
            intrinsic = np.maximum(spot_prices - self.strike, 0)
        else:
            intrinsic = np.maximum(self.strike - spot_prices, 0)
        return (intrinsic - self.premium) * self.position * self.multiplier

class OptionStrategy:
    def __init__(self, name="期权策略"):
        self.name = name
        self.legs = []

    def add_leg(self, option_type, strike, premium, position='long', multiplier=1):
        self.legs.append(Option(option_type, strike, premium, position, multiplier))

    def analyze_for_dashboard_plotly(self, spot_min, spot_max, steps=500):
        spot_prices = np.linspace(spot_min, spot_max, steps)
        total_payoff = np.zeros_like(spot_prices, dtype=float)
        
        fig = go.Figure()

        # 画出单腿盈亏虚线
        for leg in self.legs:
            leg_payoff = leg.calculate_payoff(spot_prices)
            total_payoff += leg_payoff
            
            action = "买入" if leg.position == 1 else "卖出"
            opt_type = "认购" if leg.type == 'call' else "认沽"
            leg_name = f"{action}{opt_type}_{leg.strike}"
            
            fig.add_trace(go.Scatter(
                x=spot_prices, y=leg_payoff, 
                mode='lines', 
                name=leg_name,
                line=dict(dash='dash'),
                opacity=0.4,
                hovertemplate='%{y:.2f}<extra></extra>' 
            ))

        # 画出组合总净盈亏线
        fig.add_trace(go.Scatter(
            x=spot_prices, y=total_payoff, 
            mode='lines', 
            name='组合净盈亏',
            line=dict(color='red', width=3),
            fill='tozeroy', 
            fillcolor='rgba(255, 0, 0, 0.1)',
            hovertemplate='<b>标的价格: %{x:.2f}</b><br><span style="color:red;font-size:16px;">总净盈亏: %{y:.2f}</span><extra></extra>' 
        ))

        # 计算盈亏平衡点并标记
        zero_crossings_idx = np.where(np.diff(np.sign(total_payoff)))[0]
        breakevens = [spot_prices[i] for i in zero_crossings_idx]
        for bp in breakevens:
            fig.add_trace(go.Scatter(
                x=[bp], y=[0],
                mode='markers+text',
                marker=dict(color='green', size=10),
                text=[f"盈亏点: {bp:.1f}"],
                textposition="top center",
                name="盈亏平衡点",
                hoverinfo="skip"
            ))

        # 绘制 0 轴与优化布局
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
        fig.update_layout(
            title=f"<b>{self.name}</b> (鼠标悬浮查看具体点位盈亏)",
            xaxis_title="到期时标的价格",
            yaxis_title="净盈亏",
            hovermode="x unified",
            height=600,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        return fig, np.max(total_payoff), np.min(total_payoff), breakevens

# ==========================================
# Streamlit UI 构建 
# ==========================================
st.set_page_config(page_title="期权策略——mc", layout="wide")
st.title("🚀 期权策略分析看板 (mc版)")

with st.sidebar:
    st.header("⚙️ 全局参数设置")
    spot_min = st.number_input("图表最低价格", value=530)
    spot_max = st.number_input("图表最高价格", value=750)
    
    st.markdown("---")
    st.subheader("📊 默认行情参考数据库")
    st.caption("这里的数据仅作为下拉菜单的快捷参考，右侧面板可完全手动覆写。")
    
    initial_data = pd.DataFrame({
        "合约名称": [
            "call_600", "call_610", "call_620", "call_630", "call_640", "call_650", "call_660", "call_670", "call_680",
            "put_600", "put_610", "put_620", "put_630", "put_640", "put_650", "put_660", "put_670", "put_680"
        ],
        "最新权利金": [
            55.0, 45.0, 36.5, 28.6, 23.5, 18.8, 14.5, 10.5, 7.5,
            4.5, 6.5, 9.0, 12.6, 17.5, 22.0, 27.5, 34.0, 41.0
        ]
    })
    
    edited_df = st.data_editor(initial_data, use_container_width=True, hide_index=True)
    mock_option_chain = dict(zip(edited_df["合约名称"], edited_df["最新权利金"]))
    call_options = [name for name in mock_option_chain.keys() if name.startswith('call')]
    put_options = [name for name in mock_option_chain.keys() if name.startswith('put')]

# ==========================================
# 核心大杀器：20大策略模板全集
# ==========================================
strategy_templates = {
    "【单腿】买入认购 (Long Call)": [{"label": "买入认购", "type": "call", "default": "call_640", "pos": "long", "mult": 1}],
    "【单腿】买入认沽 (Long Put)": [{"label": "买入认沽", "type": "put", "default": "put_640", "pos": "long", "mult": 1}],
    "【单腿】卖出认购 (Short Call)": [{"label": "卖出认购", "type": "call", "default": "call_640", "pos": "short", "mult": 1}],
    "【单腿】卖出认沽 (Short Put)": [{"label": "卖出认沽", "type": "put", "default": "put_640", "pos": "short", "mult": 1}],

    "【垂直价差】牛市看涨价差 (Bull Call Spread)": [
        {"label": "买入低位认购", "type": "call", "default": "call_630", "pos": "long", "mult": 1},
        {"label": "卖出高位认购", "type": "call", "default": "call_650", "pos": "short", "mult": 1}
    ],
    "【垂直价差】熊市看跌价差 (Bear Put Spread)": [
        {"label": "买入高位认沽", "type": "put", "default": "put_650", "pos": "long", "mult": 1},
        {"label": "卖出低位认沽", "type": "put", "default": "put_630", "pos": "short", "mult": 1}
    ],
    "【垂直价差】牛市看跌价差 (Bull Put Spread)": [
        {"label": "买入低位认沽", "type": "put", "default": "put_630", "pos": "long", "mult": 1},
        {"label": "卖出高位认沽", "type": "put", "default": "put_650", "pos": "short", "mult": 1}
    ],
    "【垂直价差】熊市看涨价差 (Bear Call Spread)": [
        {"label": "买入高位认购", "type": "call", "default": "call_650", "pos": "long", "mult": 1},
        {"label": "卖出低位认购", "type": "call", "default": "call_630", "pos": "short", "mult": 1}
    ],

    "【波动率】买入跨式 (Long Straddle)": [
        {"label": "买入平值认购", "type": "call", "default": "call_640", "pos": "long", "mult": 1},
        {"label": "买入平值认沽", "type": "put", "default": "put_640", "pos": "long", "mult": 1}
    ],
    "【波动率】卖出跨式 (Short Straddle)": [
        {"label": "卖出平值认购", "type": "call", "default": "call_640", "pos": "short", "mult": 1},
        {"label": "卖出平值认沽", "type": "put", "default": "put_640", "pos": "short", "mult": 1}
    ],
    "【波动率】买入宽跨式 (Long Strangle)": [
        {"label": "买入虚值认购", "type": "call", "default": "call_660", "pos": "long", "mult": 1},
        {"label": "买入虚值认沽", "type": "put", "default": "put_620", "pos": "long", "mult": 1}
    ],
    "【波动率】卖出宽跨式 (Short Strangle)": [
        {"label": "卖出虚值认购", "type": "call", "default": "call_660", "pos": "short", "mult": 1},
        {"label": "卖出虚值认沽", "type": "put", "default": "put_620", "pos": "short", "mult": 1}
    ],

    "【蝶式/鹰式】买入认购蝶式 (Long Call Butterfly)": [
        {"label": "买入低位认购", "type": "call", "default": "call_620", "pos": "long", "mult": 1},
        {"label": "卖出中位认购", "type": "call", "default": "call_640", "pos": "short", "mult": 2},
        {"label": "买入高位认购", "type": "call", "default": "call_660", "pos": "long", "mult": 1}
    ],
    "【蝶式/鹰式】铁蝴蝶 (Iron Butterfly)": [
        {"label": "买入低位认沽", "type": "put", "default": "put_620", "pos": "long", "mult": 1},
        {"label": "卖出中位认沽", "type": "put", "default": "put_640", "pos": "short", "mult": 1},
        {"label": "卖出中位认购", "type": "call", "default": "call_640", "pos": "short", "mult": 1},
        {"label": "买入高位认购", "type": "call", "default": "call_660", "pos": "long", "mult": 1}
    ],
    "【蝶式/鹰式】铁鹰式 (Iron Condor)": [
        {"label": "买入极低认沽", "type": "put", "default": "put_600", "pos": "long", "mult": 1},
        {"label": "卖出偏低认沽", "type": "put", "default": "put_620", "pos": "short", "mult": 1},
        {"label": "卖出偏高认购", "type": "call", "default": "call_660", "pos": "short", "mult": 1},
        {"label": "买入极高认购", "type": "call", "default": "call_680", "pos": "long", "mult": 1}
    ],

    "【比例价差】看涨反向比例价差 (Call Ratio Backspread)": [
        {"label": "卖出平值认购", "type": "call", "default": "call_630", "pos": "short", "mult": 1},
        {"label": "买入虚值认购 [双倍]", "type": "call", "default": "call_650", "pos": "long", "mult": 2}
    ],
    "【比例价差】看跌反向比例价差 (Put Ratio Backspread)": [
        {"label": "卖出平值认沽", "type": "put", "default": "put_650", "pos": "short", "mult": 1},
        {"label": "买入虚值认沽 [双倍]", "type": "put", "default": "put_630", "pos": "long", "mult": 2}
    ]
}

strategy_choice = st.selectbox("🎯 选择一键预设模板 (载入后可下方自由修改)", list(strategy_templates.keys()))
st.markdown("### 🛠️ 自由策略构建器")
st.caption("在这里，你可以无视左侧的数据库，强行输入任何行权价和权利金，甚至改变合约数量。")

strategy = OptionStrategy(strategy_choice)
template = strategy_templates[strategy_choice]
cols = st.columns(len(template))

try:
    for i, leg_def in enumerate(template):
        with cols[i]:
            st.markdown(f"**Leg {i+1}: {leg_def['label']}**")
            
            # --- 快速载入区 ---
            options_list = call_options if leg_def["type"] == "call" else put_options
            default_val = leg_def["default"]
            default_idx = options_list.index(default_val) if default_val in options_list else 0
            
            # 下拉菜单的 key 也加上策略名，防止跨策略冲突
            selected_contract = st.selectbox("从库中提取参考价", options_list, index=default_idx, key=f"sel_{strategy_choice}_{i}", label_visibility="collapsed")
            
            # 从选择的合约中提取出默认数字
            auto_strike = float(selected_contract.split('_')[1])
            auto_premium = float(mock_option_chain[selected_contract])
            
            # ==========================================
            # 🚀 修复 Bug 的魔法：生成动态的 Widget Key
            # 把策略名、第几条腿、选中的合约名全拼在一起！
            # ==========================================
            dynamic_key = f"{strategy_choice}_leg{i}_{selected_contract}"
            
            # --- 核心改造：自由魔改区 (支持任意输入) ---
            col_a, col_b = st.columns(2)
            with col_a:
                # 绑定动态 key
                strike_price = st.number_input("行权价 (K)", value=auto_strike, step=5.0, format="%.1f", key=f"k_{dynamic_key}")
            with col_b:
                # 绑定动态 key
                premium = st.number_input("权利金 (P)", value=auto_premium, step=0.5, format="%.2f", key=f"p_{dynamic_key}")
                
            col_c, col_d = st.columns(2)
            with col_c:
                # 手数也绑定动态 key
                leg_mult = st.number_input("手数/乘数", value=leg_def["mult"], min_value=1, step=1, key=f"m_{dynamic_key}")
            with col_d:
                action_str = "🔴 卖出" if leg_def["pos"] == "short" else "🟢 买入"
                st.info(action_str)
            
            # 把提取到的参数加进去计算！
            strategy.add_leg(
                option_type=leg_def["type"], 
                strike=strike_price, 
                premium=premium, 
                position=leg_def["pos"], 
                multiplier=leg_mult
            )

    st.markdown("---")
    
    fig, max_p, max_l, bes = strategy.analyze_for_dashboard_plotly(spot_min, spot_max)

    display_p = "理论无限" if max_p > 1000 or (max_p == max_p and np.isinf(max_p)) else f"{max_p:.2f}"
    display_l = "理论无限" if max_l < -1000 or (max_l == max_l and np.isinf(max_l)) else f"{max_l:.2f}"

    col1, col2, col3 = st.columns(3)
    col1.metric("最大潜在盈利", display_p)
    col2.metric("最大潜在亏损", display_l)
    col3.metric("盈亏平衡点", ", ".join([f"{bp:.2f}" for bp in bes]) if bes else "无")

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ 组装策略时出现错误: {e}")