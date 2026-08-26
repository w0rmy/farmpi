# Controlled paddock rename

“Rename Paddock A to North Flat” is parsed as an administrative request, not a query for Qwen. FarmPi resolves the source through the active paddocks table, validates the new human-readable name, rejects invalid/duplicate/current names, and returns an explicit confirmation request.

The browser keeps an opaque confirmation ID only in memory. A following “confirm” or “yes” within five minutes applies the update. The action layer then updates the display name and inserts a paddock_admin_audit row. No model token authorises or executes the mutation.

Because readings point to numeric sensor/paddock IDs, the prior rows automatically appear under North Flat. Dynamic resolution allows future questions to use North Flat rather than requiring a Paddock A regex.
