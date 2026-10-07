"""
Professional in-app notifications with optional sound.
"""

import streamlit as st


def show_notification(message: str, notification_type: str = "success", play_sound: bool = True) -> None:
    """Display a styled notification banner and optionally play a subtle sound."""
    icons = {
        "success": "✅",
        "error": "❌",
        "info": "ℹ️",
        "warning": "⚠️",
    }
    icon = icons.get(notification_type, "ℹ️")
    css_class = notification_type if notification_type in icons else "info"

    st.markdown(
        f"""
        <div class="notification-banner notification-{css_class}">
            <span class="notification-icon">{icon}</span>
            <span>{message}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if play_sound:
        freq = {"success": 880, "error": 440, "info": 660, "warning": 550}.get(notification_type, 660)
        st.markdown(
            f"""
            <script>
            (function() {{
                try {{
                    var ctx = new (window.AudioContext || window.webkitAudioContext)();
                    var osc = ctx.createOscillator();
                    var gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.frequency.value = {freq};
                    osc.type = 'sine';
                    gain.gain.setValueAtTime(0.08, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.3);
                }} catch(e) {{}}
            }})();
            </script>
            """,
            unsafe_allow_html=True,
        )


def set_notification(message: str, notification_type: str = "success") -> None:
    st.session_state.notification_message = message
    st.session_state.notification_type = notification_type


def render_pending_notification() -> None:
    if st.session_state.get("notification_message"):
        show_notification(
            st.session_state.notification_message,
            st.session_state.get("notification_type", "success"),
        )
        st.session_state.notification_message = None
        st.session_state.notification_type = None
