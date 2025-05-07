package com.sentimark.data.repository;

import com.sentimark.data.config.FeatureDecisions;
import com.sentimark.data.config.FeatureFlagService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.when;

public class FeatureDecisionsTest {

    @Mock
    private FeatureFlagService featureFlagService;

    private FeatureDecisions featureDecisions;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
        featureDecisions = new FeatureDecisions(featureFlagService);
    }

    @Test
    public void shouldUsePostgresBackendByDefault() {
        // Given
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);

        // When/Then
        assertFalse(featureDecisions.useIcebergBackend());
    }

    @Test
    public void shouldUseIcebergBackendWhenEnabled() {
        // Given
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);

        // When/Then
        assertTrue(featureDecisions.useIcebergBackend());
    }

    @Test
    public void shouldNotUseIcebergOptimizationsWhenBackendDisabled() {
        // Given
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        when(featureFlagService.isEnabled("use-iceberg-optimizations")).thenReturn(true);

        // When/Then
        assertFalse(featureDecisions.useIcebergOptimizations());
    }

    @Test
    public void shouldUseIcebergOptimizationsWhenBothEnabled() {
        // Given
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        when(featureFlagService.isEnabled("use-iceberg-optimizations")).thenReturn(true);

        // When/Then
        assertTrue(featureDecisions.useIcebergOptimizations());
    }

    @Test
    public void shouldNotUseIcebergPartitioningWhenBackendDisabled() {
        // Given
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        when(featureFlagService.isEnabled("use-iceberg-partitioning")).thenReturn(true);

        // When/Then
        assertFalse(featureDecisions.useIcebergPartitioning());
    }

    @Test
    public void shouldUseIcebergPartitioningWhenBothEnabled() {
        // Given
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        when(featureFlagService.isEnabled("use-iceberg-partitioning")).thenReturn(true);

        // When/Then
        assertTrue(featureDecisions.useIcebergPartitioning());
    }
}