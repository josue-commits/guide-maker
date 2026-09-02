"""DM tool adapters.

`manual` (default) writes a bundle you paste into any tool and never touches
the network. `leadshark` talks to the LeadShark REST API. Add your own by
subclassing adapters.base.DMTool and registering it in adapters.base.PROVIDERS.
"""

from .base import PROVIDERS, DMTool, get_adapter  # noqa: F401
