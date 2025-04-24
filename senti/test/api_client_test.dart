import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:senti/api/api_client.dart';
import 'package:senti/models/data_flow_point.dart';

void main() {
  group('ApiClient.getDataFlow', () {
    late ApiClient apiClient;
    
    // Sample mock response
    final mockDataFlowResponse = [
      {
        "timestamp": "2025-04-23T22:00:00",
        "messages_per_second": 0.0,
        "avg_processing_time": 0.05,
        "error_rate": 0.0
      },
      {
        "timestamp": "2025-04-23T23:00:00",
        "messages_per_second": 10.0,
        "avg_processing_time": 0.08,
        "error_rate": 0.01
      },
      {
        "timestamp": "2025-04-24T00:00:00",
        "messages_per_second": 25.0,
        "avg_processing_time": 0.12,
        "error_rate": 0.02
      }
    ];
    
    setUp(() {
      // Create a mock HTTP client
      final mockClient = MockClient((request) async {
        // Check if the request is for the dataflow endpoint
        if (request.url.path.contains('/sentiment/dataflow')) {
          return http.Response(
            jsonEncode(mockDataFlowResponse),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        
        // Return 404 for all other requests
        return http.Response('Not found', 404);
      });
      
      // Create ApiClient with the mock client
      apiClient = ApiClient(baseUrl: 'http://test.example.com', client: mockClient);
      apiClient.setAuthToken('test_token');
    });
    
    test('parses data flow response correctly', () async {
      // Call the getDataFlow method
      final result = await apiClient.getDataFlow(points: 3);
      
      // Check the result
      expect(result, isA<List<DataFlowPoint>>());
      expect(result.length, equals(3));
      
      // Check first point
      expect(result[0].timestamp.toIso8601String().startsWith('2025-04-23T22:00:00'), isTrue);
      expect(result[0].messagesPerSecond, equals(0.0));
      expect(result[0].avgProcessingTime, equals(0.05));
      expect(result[0].errorRate, equals(0.0));
      
      // Check second point
      expect(result[1].timestamp.toIso8601String().startsWith('2025-04-23T23:00:00'), isTrue);
      expect(result[1].messagesPerSecond, equals(10.0));
      expect(result[1].avgProcessingTime, equals(0.08));
      expect(result[1].errorRate, equals(0.01));
      
      // Check third point
      expect(result[2].timestamp.toIso8601String().startsWith('2025-04-24T00:00:00'), isTrue);
      expect(result[2].messagesPerSecond, equals(25.0));
      expect(result[2].avgProcessingTime, equals(0.12));
      expect(result[2].errorRate, equals(0.02));
    });
    
    test('handles empty response', () async {
      // Create a new mock client that returns an empty array
      final emptyMockClient = MockClient((request) async {
        return http.Response('[]', 200, headers: {'content-type': 'application/json'});
      });
      
      // Create a new ApiClient with the empty mock client
      final emptyApiClient = ApiClient(baseUrl: 'http://test.example.com', client: emptyMockClient);
      
      // Call the getDataFlow method
      final result = await emptyApiClient.getDataFlow();
      
      // Check the result
      expect(result, isA<List<DataFlowPoint>>());
      expect(result, isEmpty);
    });
    
    test('handles server error', () async {
      // Create a new mock client that returns a server error
      final errorMockClient = MockClient((request) async {
        return http.Response('Server error', 500);
      });
      
      // Create a new ApiClient with the error mock client
      final errorApiClient = ApiClient(baseUrl: 'http://test.example.com', client: errorMockClient);
      
      // Expect an exception when calling getDataFlow
      expect(
        () => errorApiClient.getDataFlow(),
        throwsA(predicate((e) => e.toString().contains('Server error'))),
      );
    });
  });
}