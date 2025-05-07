# RT Sentiment Analysis - Azure AKS Node Pools

# Create a dedicated node pool for data processing using spot instances
resource "azurerm_kubernetes_cluster_node_pool" "data_nodes_spot" {
  name                   = "dataspots"  # Changed name to avoid conflict with existing node pool
  kubernetes_cluster_id  = azurerm_kubernetes_cluster.aks.id
  vm_size                = "Standard_D2s_v3"  # Small VMs for SIT environment (2 vCPUs)
  node_count             = 1                  # Reduced to 1 node for SIT
  os_disk_size_gb        = 128                # Reduced from 200GB
  proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
  
  # Spot instance configuration for cost savings (up to 90% discount)
  priority               = "Spot"         # Use spot instances
  eviction_policy        = "Delete"       # Delete VM when evicted
  spot_max_price         = -1             # -1 means pay the current spot price (up to on-demand price)
  
  # Taints to ensure only specific workloads are scheduled
  # Adding spot taint so only pods that tolerate spot instances run here
  node_taints           = [
    "workload=dataprocessing:NoSchedule",
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ]
  
  # PPG cannot be used with multiple zones - must use no zones or a single zone
  zones                 = []
  
  tags = {
    environment = var.environment
    nodepool    = "data"
    ppg         = var.ppg_name
    priority    = "spot"
  }

  # Enable this node pool conditionally based on flag to help with quota management
  count                  = var.enable_spot_instances ? 1 : 0
}

# Create a dedicated node pool for low-latency workloads using spot instances
resource "azurerm_kubernetes_cluster_node_pool" "low_latency_spot" {
  name                   = "lowspots"  # Changed name to avoid conflict with existing node pool
  kubernetes_cluster_id  = azurerm_kubernetes_cluster.aks.id
  vm_size                = "Standard_F2s_v2"  # Smaller F-series VM (2 vCPUs)
  node_count             = 1                  # Reduced to 1 node for SIT
  os_disk_size_gb        = 64                 # Reduced from 100GB
  proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
  
  # Spot instance configuration for cost savings (up to 90% discount)
  priority               = "Spot"         # Use spot instances
  eviction_policy        = "Delete"       # Delete VM when evicted
  spot_max_price         = -1             # -1 means pay the current spot price (up to on-demand price)
  
  # Taints to ensure only specific workloads are scheduled
  # Adding spot taint so only pods that tolerate spot instances run here
  node_taints           = [
    "workload=lowlatency:NoSchedule",
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ]
  
  # PPG cannot be used with multiple zones - must use no zones or a single zone
  zones                 = []
  
  tags = {
    environment = var.environment
    nodepool    = "lowlatency"
    ppg         = var.ppg_name
    priority    = "spot"
  }
  
  # Only create this if we have enough spot quota or if we want to use the standard node pool
  count                  = var.enable_spot_instances && var.use_low_latency_pool ? 1 : 0
}