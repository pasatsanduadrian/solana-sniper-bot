# gradio_ui.py - Dashboard îmbunătățit
import argparse
import asyncio
import gradio as gr
from datetime import datetime

from src.bot import FeedAggregator, TradingEngine, setup_logging

def launch_dashboard(share: bool = False) -> None:
    """Launch enhanced Gradio interface."""
    
    setup_logging()
    feeds = FeedAggregator()
    engine = TradingEngine(feeds)
    
    async def start_bot() -> str:
        await feeds.start()
        await engine.start()
        return "✅ Bot started successfully"
    
    async def stop_bot() -> str:
        await engine.stop()
        await feeds.stop()
        return "🛑 Bot stopped"
    
    def get_token_data() -> str:
        """Format token data for display."""
        tokens = feeds.get_top_tokens(10)
        if not tokens:
            return "No tokens found yet..."
            
        lines = ["🎯 Top Trading Opportunities:\n"]
        for i, token in enumerate(tokens, 1):
            lines.append(f"{i}. {token.symbol} ({token.address[:8]}...)")
            lines.append(f"   Price: ${token.price:.6f} | Change 5m: {token.price_change_5m:+.2f}%")
            lines.append(f"   Volume 5m: ${token.volume_5m:,.0f} | Liquidity: ${token.liquidity:,.0f}")
            opp = f" | Opportunity: {token.opportunity}" if token.opportunity else ""
            lines.append(f"   Score: {token.score:.1f}/100{opp}\n")
            
        return "\n".join(lines)
    
    def get_positions() -> str:
        """Format position data."""
        if not engine.positions:
            return "No open positions"
            
        lines = ["📊 Open Positions:\n"]
        for pos in engine.positions.values():
            duration = (datetime.utcnow() - pos.entry_time).total_seconds() / 60
            lines.append(f"• {pos.token.symbol}")
            lines.append(f"  Entry: ${pos.entry_price:.6f} | Current: ${pos.token.price:.6f}")
            lines.append(f"  PnL: ${pos.pnl:.2f} ({pos.pnl_percent:+.2f}%)")
            lines.append(f"  Duration: {duration:.1f} minutes\n")
            
        return "\n".join(lines)
    
    def get_stats() -> str:
        """Format trading statistics."""
        stats = engine.get_stats()
        
        return f"""📈 Trading Statistics:
        
Total Invested: ${stats['total_invested']:.2f}
Open Positions: {stats['positions']}
Open PnL: ${stats['open_pnl']:+.2f}
Realized PnL: ${stats['realized_pnl']:+.2f}
Total PnL: ${stats['total_pnl']:+.2f}
ROI: {stats['roi_percent']:+.2f}%
"""
    
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🚀 Solana Meme-Coin Sniper Bot
        
        Real-time trading bot for Solana tokens with automated entry/exit strategies.
        """)
        
        with gr.Row():
            start_btn = gr.Button("▶️ Start Bot", variant="primary")
            stop_btn = gr.Button("⏹️ Stop Bot", variant="stop")
            status = gr.Textbox(label="Status", value="Bot inactive")
            
        with gr.Row():
            with gr.Column():
                tokens_display = gr.Textbox(
                    label="Token Scanner", 
                    value="Waiting for data...",
                    lines=15
                )
                
            with gr.Column():
                positions_display = gr.Textbox(
                    label="Active Positions",
                    value="No positions",
                    lines=7
                )
                
                stats_display = gr.Textbox(
                    label="Performance",
                    value="No data",
                    lines=7
                )
        
        # Auto-refresh displays
        def refresh_displays():
            return get_token_data(), get_positions(), get_stats()
        
        # Set up event handlers
        start_btn.click(start_bot, outputs=status)
        stop_btn.click(stop_bot, outputs=status)
        
        # Auto-refresh every 5 seconds
        demo.load(
            refresh_displays, 
            outputs=[tokens_display, positions_display, stats_display],
            every=5
        )
    
    demo.launch(share=share, server_name="0.0.0.0")

def main() -> None:
    """Entry point for CLI execution."""
    parser = argparse.ArgumentParser(description="Launch the Gradio dashboard")
    parser.add_argument(
        "--share",
        action="store_true", 
        help="Create a public gradio link",
    )
    args = parser.parse_args()
    launch_dashboard(share=args.share)

if __name__ == "__main__":
    main()
