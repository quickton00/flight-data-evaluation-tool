"""
Custom CustomTkinter widgets for the Flight Data Evaluation Tool.

This module provides specialized CustomTkinter widgets including collapsible
panels for organizing evaluation results and tabbed views for displaying
performance tiers across different flight phases.
"""

import customtkinter


class CTkCollapsiblePanel(customtkinter.CTkFrame):
    """
    A collapsible panel widget with expand/collapse functionality.

    This widget provides a clickable header that toggles the visibility of its
    content frame. Useful for organizing large amounts of information in a
    compact, expandable format.

    :param master: The parent widget.
    :type master: tkinter.Widget
    :param title: Title text displayed in the header button.
    :type title: str
    :param args: Additional positional arguments passed to CTkFrame.
    :type args: tuple
    :param kwargs: Additional keyword arguments passed to CTkFrame.
    :type kwargs: dict

    :ivar title: Formatted title string with expand/collapse indicator.
    :vartype title: str
    :ivar _collapsed: Current collapse state of the panel.
    :vartype _collapsed: bool
    :ivar header_frame: Frame containing the header button.
    :vartype header_frame: customtkinter.CTkFrame
    :ivar _content_frame: Frame containing the panel's content (shown/hidden on toggle).
    :vartype _content_frame: customtkinter.CTkFrame
    :ivar header_button: Clickable button in the header for toggling collapse state.
    :vartype header_button: customtkinter.CTkButton

    .. note::
       The panel starts in a collapsed state. It will only expand if the content
       frame contains widgets. Use _content_frame to add widgets to the panel.
    """
    def __init__(self, master, title, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.title = "▸ " + title

        self._collapsed = True

        self.header_frame = customtkinter.CTkFrame(self)
        self.header_frame.pack(fill="x")

        self._content_frame = customtkinter.CTkFrame(self)

        self.header_button = customtkinter.CTkButton(
            self.header_frame,
            text=self.title,
            command=self.toggle,
            anchor="w",
            font=(None, 16),
        )
        self.header_button.pack(fill="x", padx=5, pady=2)

    def toggle(self):
        """
        Toggle the expand/collapse state of the panel.

        This method expands the content frame if collapsed and collapses it if expanded.
        The header button icon changes between '▸' (collapsed) and '▾' (expanded).

        .. note::
           The panel will not expand if the content frame is empty (has no child widgets).
        """
        text = self.header_button.cget("text")[2:]

        # Only expand if content frame is not empty
        if self._collapsed and not self._content_frame.winfo_children():
            return

        if self._collapsed:
            self._content_frame.pack(fill="x", expand=False)
            self.header_button.configure(text="▾ " + text)
        else:
            self._content_frame.pack_forget()
            self.header_button.configure(text="▸ " + text)
        self._collapsed = not self._collapsed


class PhasesTabView(customtkinter.CTkTabview):
    """
    Tabbed view widget for displaying flight phase evaluation results.

    This custom widget creates a tabbed interface with one tab per flight phase
    (Alignment, Approach, Final Approach, Total Flight). Each tab contains
    collapsible panels for different performance tiers (Excellent, Good, Normal,
    Poor, Very Poor, Not Tierable).

    :param master: The parent widget.
    :type master: tkinter.Widget
    :param kwargs: Additional keyword arguments passed to CTkTabview.
    :type kwargs: dict

    :ivar tabs: List of tab names for flight phases.
    :vartype tabs: list of str
    :ivar evaluation_tiers: Dictionary mapping tier names to their color hex codes.
    :vartype evaluation_tiers: dict
    :ivar panels: Nested dictionary structure: {tab_name: {tier_name: CTkCollapsiblePanel}}.
    :vartype panels: dict

    .. note::
       Each tier panel is color-coded according to performance level, with a
       slightly darker hover color for visual feedback.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # create tabs
        self.tabs = ["Alignment Phase", "Approach Phase", "Final Approach Phase", "Total Flight"]
        self.evaluation_tiers = {
            "Excellent": "#00ab41",
            "Good": "#1AA260",
            "Normal": "#f39c11",
            "Poor": "#E55451",
            "Very Poor": "#ED2939",
            "Not Tierable": "#808080",
        }
        self.panels = {tab: {} for tab in self.tabs}

        for tab in self.tabs:
            self.add(tab)
            scrollableFrame = customtkinter.CTkScrollableFrame(self.tab(tab), width=1000, height=600)
            scrollableFrame.pack(fill="both", expand=True, padx=15, pady=15)

            for evaluation_tier, color in self.evaluation_tiers.items():
                self.panels[tab][evaluation_tier] = CTkCollapsiblePanel(scrollableFrame, title=evaluation_tier)
                self.panels[tab][evaluation_tier].pack(fill="x", pady=10, padx=10)

                self.panels[tab][evaluation_tier].header_button.configure(fg_color=color)

                # Get current color and make it 15% darker for hover effect
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                darker_factor = 0.85
                darker_color = f"#{int(r * darker_factor):02x}{int(g * darker_factor):02x}{int(b * darker_factor):02x}"
                self.panels[tab][evaluation_tier].header_button.configure(hover_color=darker_color)
