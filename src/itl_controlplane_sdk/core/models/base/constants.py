"""
Constants for the ITL ControlPlane SDK.

Provider namespaces, resource types, and location definitions.
"""

# Provider namespace
PROVIDER_NAMESPACE = "ITL.Core"

# Resource types
RESOURCE_TYPE_RESOURCE_GROUPS = "resourcegroups"
RESOURCE_TYPE_MANAGEMENT_GROUPS = "managementgroups"
RESOURCE_TYPE_DEPLOYMENTS = "deployments"
RESOURCE_TYPE_SUBSCRIPTIONS = "subscriptions"
RESOURCE_TYPE_TAGS = "tags"
RESOURCE_TYPE_POLICIES = "policies"
RESOURCE_TYPE_LOCATIONS = "locations"
RESOURCE_TYPE_EXTENDED_LOCATIONS = "extendedlocations"
RESOURCE_TYPE_TENANTS = "tenants"

# Default tenant
DEFAULT_TENANT_ID = "ITL"

ITL_RESOURCE_TYPES = [
    RESOURCE_TYPE_TENANTS,
    RESOURCE_TYPE_RESOURCE_GROUPS,
    RESOURCE_TYPE_MANAGEMENT_GROUPS,
    RESOURCE_TYPE_DEPLOYMENTS,
    RESOURCE_TYPE_SUBSCRIPTIONS,
    RESOURCE_TYPE_TAGS,
    RESOURCE_TYPE_POLICIES,
    RESOURCE_TYPE_LOCATIONS,
    RESOURCE_TYPE_EXTENDED_LOCATIONS,
]

# Extended (edge / CDN) locations
EXTENDED_LOCATIONS = [
    {"name": "cdn-london", "display_name": "CDN London Edge", "shortname": "CDL", "region": "United Kingdom", "location_type": "EdgeZone"},
    {"name": "cdn-frankfurt", "display_name": "CDN Frankfurt Edge", "shortname": "CDF", "region": "Germany", "location_type": "EdgeZone"},
    {"name": "cdn-paris", "display_name": "CDN Paris Edge", "shortname": "CDP", "region": "France", "location_type": "EdgeZone"},
    {"name": "cdn-amsterdam", "display_name": "CDN Amsterdam Edge", "shortname": "CDA", "region": "Netherlands", "location_type": "EdgeZone"},
    {"name": "cdn-stockholm", "display_name": "CDN Stockholm Edge", "shortname": "CDS", "region": "Sweden", "location_type": "EdgeZone"},
    {"name": "cdn-zurich", "display_name": "CDN Zurich Edge", "shortname": "CDZ", "region": "Switzerland", "location_type": "EdgeZone"},
]

# Default cloud locations
DEFAULT_LOCATIONS = [
    # United States
    {"name": "eastus", "display_name": "East US", "shortname": "EUS", "region": "United States"},
    {"name": "westus", "display_name": "West US", "shortname": "WUS", "region": "United States"},
    {"name": "centralus", "display_name": "Central US", "shortname": "CUS", "region": "United States"},
    # United Kingdom
    {"name": "uksouth", "display_name": "UK South", "shortname": "UKS", "region": "United Kingdom"},
    {"name": "ukwest", "display_name": "UK West", "shortname": "UKW", "region": "United Kingdom"},
    # Europe - Regional
    {"name": "northeurope", "display_name": "North Europe", "shortname": "NOR", "region": "Europe"},
    {"name": "westeurope", "display_name": "West Europe", "shortname": "WES", "region": "Europe"},
    # Europe - Major Cities
    {"name": "germanywestcentral", "display_name": "Germany West Central", "shortname": "GWC", "region": "Germany"},
    {"name": "francecentral", "display_name": "France Central", "shortname": "FRA", "region": "France"},
    {"name": "switzerlandnorth", "display_name": "Switzerland North", "shortname": "SWI", "region": "Switzerland"},
    {"name": "swedencentral", "display_name": "Sweden Central", "shortname": "SWE", "region": "Sweden"},
    {"name": "italynorth", "display_name": "Italy North", "shortname": "ITA", "region": "Italy"},
    {"name": "polandcentral", "display_name": "Poland Central", "shortname": "POL", "region": "Poland"},
    {"name": "amsterdam", "display_name": "Amsterdam", "shortname": "AMS", "region": "Netherlands"},
    {"name": "rotterdam", "display_name": "Rotterdam", "shortname": "RTM", "region": "Netherlands"},
    {"name": "almere", "display_name": "Almere", "shortname": "ALM", "region": "Netherlands"},
    # Asia Pacific
    {"name": "southeastasia", "display_name": "Southeast Asia", "shortname": "SEA", "region": "Asia Pacific"},
    {"name": "eastasia", "display_name": "East Asia", "shortname": "EAS", "region": "Asia Pacific"},
] + EXTENDED_LOCATIONS
