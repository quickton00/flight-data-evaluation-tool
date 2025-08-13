import customtkinter


class CTkCollapsiblePanel(customtkinter.CTkFrame):
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
