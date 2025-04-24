import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:senti/api/api_client.dart';
import 'package:senti/models/data_flow_point.dart';
import 'package:senti/providers/dashboard_provider.dart';
import 'package:senti/services/websocket_service.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';

// Generate mock classes
@GenerateMocks([ApiClient, WebSocketService])
import 'dashboard_provider_test.mocks.dart';

// This test is designed to verify the DashboardProvider's loadDataFlow method works correctly

void main() {
  group('DashboardProvider.loadDataFlow', () {
    late MockApiClient mockApiClient;
    late MockWebSocketService mockWebSocketService;
    late DashboardProvider dashboardProvider;

    setUp(() {
      // Create mock ApiClient
      mockApiClient = MockApiClient();
      
      // Create a proper mock WebSocketService with the necessary behavior
      mockWebSocketService = MockWebSocketService();
      when(mockWebSocketService.isConnected).thenReturn(false);
      final controller = StreamController<bool>.broadcast();
      controller.add(false);
      when(mockWebSocketService.connectionStatusStream).thenAnswer((_) => controller.stream);
      
      // Create DashboardProvider with mocks
      dashboardProvider = DashboardProvider(mockApiClient, mockWebSocketService);
    });

    test('loads data flow points successfully', () async {
      // Create mock data flow points
      final mockDataPoints = [
        DataFlowPoint(
          timestamp: DateTime(2025, 4, 23, 22),
          messagesPerSecond: 10.0,
          avgProcessingTime: 0.05,
          errorRate: 0.01,
        ),
        DataFlowPoint(
          timestamp: DateTime(2025, 4, 23, 23),
          messagesPerSecond: 15.0,
          avgProcessingTime: 0.04,
          errorRate: 0.02,
        ),
      ];
      
      // Setup mock ApiClient to return mock data
      when(mockApiClient.getDataFlow(points: 30))
          .thenAnswer((_) async => mockDataPoints);
          
      // Call the loadDataFlow method
      await dashboardProvider.loadDataFlow();
      
      // Verify the expected behavior - gets called once through loadDataFlow 
      // and once through constructor's loadAllDashboardData
      verify(mockApiClient.getDataFlow(points: 30)).called(2);
      
      // Check the state of the dashboardProvider
      expect(dashboardProvider.isLoadingDataFlow, false);
      expect(dashboardProvider.dataFlowError, null);
      expect(dashboardProvider.dataFlowPoints, equals(mockDataPoints));
    });
    
    test('handles error during loading', () async {
      // Setup mock ApiClient to throw an error
      when(mockApiClient.getDataFlow(points: 30))
          .thenThrow(Exception('Network error'));
          
      // Call the loadDataFlow method
      await dashboardProvider.loadDataFlow();
      
      // Verify the expected behavior - gets called once through loadDataFlow 
      // and once through constructor's loadAllDashboardData
      verify(mockApiClient.getDataFlow(points: 30)).called(2);
      
      // Check the state of the dashboardProvider
      expect(dashboardProvider.isLoadingDataFlow, false);
      expect(dashboardProvider.dataFlowError, isNotNull);
      expect(dashboardProvider.dataFlowError, contains('Network error'));
      expect(dashboardProvider.dataFlowPoints, isEmpty);
    });
    
    test('handles custom point parameter', () async {
      // Create mock data flow points
      final mockDataPoints = [
        DataFlowPoint(
          timestamp: DateTime(2025, 4, 23, 22),
          messagesPerSecond: 10.0,
          avgProcessingTime: 0.05,
          errorRate: 0.01,
        ),
      ];
      
      // Setup mock ApiClient to return mock data with custom points
      when(mockApiClient.getDataFlow(points: 10))
          .thenAnswer((_) async => mockDataPoints);
          
      // Call the loadDataFlow method with custom points
      await dashboardProvider.loadDataFlow(points: 10);
      
      // Verify the expected behavior
      verify(mockApiClient.getDataFlow(points: 10)).called(1);
      
      // Check the state of the dashboardProvider
      expect(dashboardProvider.dataFlowPoints, equals(mockDataPoints));
    });
  });
}