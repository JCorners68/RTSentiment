# RT Sentiment Analysis - Azure AKS Node Pools

# Create a dedicated node pool for data processing
resource "azurerm_kubernetes_cluster_node_pool" "data_nodes" {
  name                   = "datanodes"
  kubernetes_cluster_id  = azurerm_kubernetes_cluster.aks.id
  vm_size                = "Standard_D8s_v3"  # Larger VMs for data processing
  node_count             = 2
  os_disk_size_gb        = 200
  proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
  
  # Taints to ensure only specific workloads are scheduled
  node_taints           = ["workload=dataprocessing:NoSchedule"]
  
  # Use zones for high availability
  zones                 = [1, 2, 3]
  
  tags = {
    environment = "uat"
    nodepool    = "data"
    ppg         = var.ppg_name
  }
}

# Create a dedicated node pool for low-latency workloads
resource "azurerm_kubernetes_cluster_node_pool" "low_latency_nodes" {
  name                   = "lowlatency"
  kubernetes_cluster_id  = azurerm_kubernetes_cluster.aks.id
  vm_size                = "Standard_F8s_v2"  # F-series optimized for low latency
  node_count             = 2
  os_disk_size_gb        = 100
  proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
  
  # Taints to ensure only specific workloads are scheduled
  node_taints           = ["workload=lowlatency:NoSchedule"]
  
  # Use zones for high availability
  zones                 = [1, 2, 3]
  
  tags = {
    environment = "uat"
    nodepool    = "lowlatency"
    ppg         = var.ppg_name
  }
}