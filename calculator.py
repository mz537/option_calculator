import numpy as np
import matplotlib.pyplot as plt

# 设置 matplotlib 支持中文显示，避免方块乱码
plt.rcParams['font.sans-serif'] = ['SimHei', 'Songti SC', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class Option:
    """单一期权合约（Leg）类"""
    def __init__(self, option_type, strike, premium, position='long', multiplier=1):
        """
        :param option_type: 'call' (认购) 或 'put' (认沽)
        :param strike: 行权价 (K)
        :param premium: 权利金单价
        :param position: 'long' (买方) 或 'short' (卖方)
        :param multiplier: 合约乘数 (默认为1)
        """
        self.type = option_type.lower()
        self.strike = strike
        self.premium = premium
        self.position = 1 if position.lower() == 'long' else -1
        self.multiplier = multiplier

        if self.type not in ['call', 'put']:
            raise ValueError("期权类型必须是 'call' 或 'put'")

    def calculate_payoff(self, spot_prices):
        """计算到期盈亏"""
        if self.type == 'call':
            # 认购期权到期价值：Max(S - K, 0)
            intrinsic_value = np.maximum(spot_prices - self.strike, 0)
        else:
            # 认沽期权到期价值：Max(K - S, 0)
            intrinsic_value = np.maximum(self.strike - spot_prices, 0)
        
        # 净盈亏 = (到期价值 - 初始付出的权利金) * 头寸方向 * 合约乘数
        net_profit = (intrinsic_value - self.premium) * self.position * self.multiplier
        return net_profit


class OptionStrategy:
    """期权组合策略类"""
    def __init__(self, name="期权策略组合"):
        self.name = name
        self.legs = []  # 存放所有期权合约的列表

    def add_leg(self, option_type, strike, premium, position='long', multiplier=1):
        """向组合中添加一条期权腿"""
        leg = Option(option_type, strike, premium, position, multiplier)
        self.legs.append(leg)
        return self # 方便链式调用

    def analyze(self, spot_min, spot_max, steps=1000):
        """
        核心分析函数：计算总盈亏、盈亏点，并绘制图表
        :param spot_min: 图表X轴标的价格下限
        :param spot_max: 图表X轴标的价格上限
        """
        # 生成标的价格数组
        spot_prices = np.linspace(spot_min, spot_max, steps)
        
        # 初始化总盈亏数组为0
        total_payoff = np.zeros_like(spot_prices, dtype=float)
        
        # 将每一条腿的盈亏累加到总盈亏中
        for leg in self.legs:
            total_payoff += leg.calculate_payoff(spot_prices)
            
        # 1. 计算最大盈利与最大亏损
        max_profit = np.max(total_payoff)
        max_loss = np.min(total_payoff)
        
        # 判断是否为理论上的"无限" (通过检查图表边缘的斜率)
        if total_payoff[-1] > total_payoff[-2] and max_profit == total_payoff[-1]:
            profit_str = "理论无限"
        else:
            profit_str = f"{max_profit:.2f}"
            
        if total_payoff[-1] < total_payoff[-2] and max_loss == total_payoff[-1]:
            loss_str = "理论无限"
        else:
            loss_str = f"{max_loss:.2f}"

        # 2. 寻找盈亏平衡点 (寻找穿过0轴的点)
        # 通过判断相邻两个点符号是否发生变化来定位0轴交叉点
        zero_crossings_idx = np.where(np.diff(np.sign(total_payoff)))[0]
        breakevens = [spot_prices[i] for i in zero_crossings_idx]

        # --- 打印分析报告 ---
        print("="*40)
        print(f"📊 策略分析报告: 【{self.name}】")
        print("-" * 40)
        print(f"📈 最大潜在盈利: {profit_str}")
        print(f"📉 最大潜在亏损: {loss_str}")
        if breakevens:
            be_str = ", ".join([f"{bp:.2f}" for bp in breakevens])
            print(f"🎯 盈亏平衡点: {be_str}")
        else:
            print("🎯 盈亏平衡点: 无 (始终盈利或始终亏损)")
        print("="*40)

        # --- 绘制图表 ---
        plt.figure(figsize=(10, 6), dpi=100)
        
        # 绘制各个单腿的盈亏线 (使用虚线和半透明)
        for i, leg in enumerate(self.legs):
            leg_payoff = leg.calculate_payoff(spot_prices)
            action_cn = "买入" if leg.position == 1 else "卖出"
            type_cn = "认购" if leg.type == 'call' else "认沽"
            label = f"{action_cn} {type_cn} 行权价={leg.strike}"
            plt.plot(spot_prices, leg_payoff, linestyle='--', alpha=0.6, label=label)

        # 绘制组合总盈亏线 (加粗实线)
        plt.plot(spot_prices, total_payoff, color='red', linewidth=3, label=f'组合总净盈亏')
        
        # 绘制0轴和盈亏平衡点标记
        plt.axhline(0, color='black', linestyle='-', linewidth=1)
        for bp in breakevens:
            plt.plot(bp, 0, marker='o', markersize=8, color='green')
            plt.annotate(f"{bp:.0f}", (bp, 0), textcoords="offset points", xytext=(0,10), ha='center', color='green')

        # 完善图表信息
        plt.fill_between(spot_prices, total_payoff, 0, where=(total_payoff >= 0), facecolor='red', alpha=0.1)
        plt.fill_between(spot_prices, total_payoff, 0, where=(total_payoff < 0), facecolor='green', alpha=0.1)
        
        plt.title(self.name, fontsize=15, fontweight='bold')
        plt.xlabel('到期时标的资产价格', fontsize=12)
        plt.ylabel('净盈亏', fontsize=12)
        plt.legend(loc='best')
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.tight_layout()
        plt.show()

# ==========================================
# 测试与使用案例
# ==========================================

if __name__ == "__main__":
    
    # 纯香草期权 (Vanilla Call) - 买入一张单腿认购
    vanilla_call = OptionStrategy("纯香草期权 - 买入认购 (Vanilla Call)")
    vanilla_call.add_leg('call', strike=640, premium=23.5, position='long', multiplier=10)
    vanilla_call.analyze(spot_min=550, spot_max=750)

    # 牛市看涨价差 (Bull Call Spread) - 我们之前讨论的原油例子
    bull_spread = OptionStrategy("牛市看涨价差 (Bull Call Spread)")
    bull_spread.add_leg('call', strike=640, premium=23.5, position='long', multiplier=1000)
    bull_spread.add_leg('call', strike=650, premium=18.8, position='short', multiplier=1000)
    bull_spread.analyze(spot_min=600, spot_max=700)

    # 做空波动率神器 - 铁鹰式策略 (Iron Condor)
    # 适用场景：预期标的价格在一个区间内震荡
    iron_condor = OptionStrategy("铁鹰式组合 (Iron Condor)")
    iron_condor.add_leg('put', strike=580, premium=5, position='long')   # 保护性买入低位认沽
    iron_condor.add_leg('put', strike=600, premium=15, position='short') # 卖出偏低位认沽
    iron_condor.add_leg('call', strike=640, premium=18, position='short')# 卖出偏高位认购
    iron_condor.add_leg('call', strike=660, premium=6, position='long')  # 保护性买入高位认购
    iron_condor.analyze(spot_min=550, spot_max=700)

    # 买入跨式策略 (Long Straddle)
    # 适用场景：预期即将发生大事件（如财报发布、非农数据、重要政策），
    # 知道标的肯定会有剧烈波动，但不知道是暴涨还是暴跌。
    # 逻辑：同时买入相同行权价的认购和认沽，只要波动够大，一边的盈利就能覆盖两边的权利金成本。
    straddle = OptionStrategy("买入跨式策略 (Long Straddle)")
    straddle.add_leg('call', strike=640, premium=23.5, position='long')
    straddle.add_leg('put', strike=640, premium=22.0, position='long')
    straddle.analyze(spot_min=550, spot_max=730)

    # 买入宽跨式策略 (Long Strangle)
    # 适用场景：和跨式类似，也是赌大波动，但跨式太贵了（买两份平值期权）。
    # 逻辑：买入虚值的认购和虚值的认沽。成本更低，但需要标的发生更大的波动才能回本。
    strangle = OptionStrategy("买入宽跨式策略 (Long Strangle)")
    strangle.add_leg('call', strike=660, premium=15.9, position='long') # 高行权价认购
    strangle.add_leg('put', strike=620, premium=12.6, position='long')  # 低行权价认沽
    strangle.analyze(spot_min=550, spot_max=730)

    # 做空波动率：卖出跨式策略 (Short Straddle)
    # 适用场景：市场极其平淡，预期未来一段时间价格会在当前位置横盘。
    # 逻辑：同时卖出认购和认沽，狂收两份权利金。但注意，这是一个“收益有限，风险无限”的策略。
    short_straddle = OptionStrategy("卖出跨式策略 (Short Straddle - 高风险)")
    short_straddle.add_leg('call', strike=640, premium=23.5, position='short')
    short_straddle.add_leg('put', strike=640, premium=22.0, position='short')
    short_straddle.analyze(spot_min=580, spot_max=700)

    # 精准狙击：买入蝶式看涨价差 (Long Call Butterfly)
    # 适用场景：预期标的在到期日会“精准”停在某一个价格上（小幅震荡）。
    # 逻辑：这是一个四腿策略（实际上是三个行权价）。它的收益图看起来像一个帐篷，成本极低，盈亏比极高，但命中难度大。
    butterfly = OptionStrategy("买入蝶式策略 (Long Call Butterfly)")
    butterfly.add_leg('call', strike=630, premium=28.6, position='long')     # 腿1：买入1份低位深度实值
    butterfly.add_leg('call', strike=640, premium=23.5, position='short')    # 腿2：卖出1份平值
    butterfly.add_leg('call', strike=640, premium=23.5, position='short')    # 腿3：再卖出1份平值 (凑齐2份空头)
    butterfly.add_leg('call', strike=650, premium=18.8, position='long')     # 腿4：买入1份高位虚值起保护作用
    butterfly.analyze(spot_min=610, spot_max=670)