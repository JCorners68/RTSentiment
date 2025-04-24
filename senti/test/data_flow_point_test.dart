import 'package:flutter_test/flutter_test.dart';
import 'package:senti/models/data_flow_point.dart';

void main() {
  group('DataFlowPoint', () {
    test('can be instantiated with required parameters', () {
      final now = DateTime.now();
      final dataFlowPoint = DataFlowPoint(
        timestamp: now,
        messagesPerSecond: 10.5,
        avgProcessingTime: 0.05,
        errorRate: 0.01,
      );

      expect(dataFlowPoint.timestamp, equals(now));
      expect(dataFlowPoint.messagesPerSecond, equals(10.5));
      expect(dataFlowPoint.avgProcessingTime, equals(0.05));
      expect(dataFlowPoint.errorRate, equals(0.01));
    });

    test('fromJson correctly parses valid JSON', () {
      final json = {
        'timestamp': '2025-04-23T22:00:00.000Z',
        'messages_per_second': 10.5,
        'avg_processing_time': 0.05,
        'error_rate': 0.01,
      };

      final dataFlowPoint = DataFlowPoint.fromJson(json);

      expect(dataFlowPoint.timestamp, equals(DateTime.parse('2025-04-23T22:00:00.000Z')));
      expect(dataFlowPoint.messagesPerSecond, equals(10.5));
      expect(dataFlowPoint.avgProcessingTime, equals(0.05));
      expect(dataFlowPoint.errorRate, equals(0.01));
    });

    test('toJson correctly serializes to JSON', () {
      final dataFlowPoint = DataFlowPoint(
        timestamp: DateTime.parse('2025-04-23T22:00:00.000Z'),
        messagesPerSecond: 10.5,
        avgProcessingTime: 0.05,
        errorRate: 0.01,
      );

      final json = dataFlowPoint.toJson();

      expect(json['timestamp'], equals('2025-04-23T22:00:00.000Z'));
      expect(json['messages_per_second'], equals(10.5));
      expect(json['avg_processing_time'], equals(0.05));
      expect(json['error_rate'], equals(0.01));
    });

    test('fromJson handles missing or invalid data', () {
      final json = {
        'timestamp': 'invalid-date',
        'messages_per_second': 'not-a-number',
        // Missing avg_processing_time and error_rate
      };

      final dataFlowPoint = DataFlowPoint.fromJson(json);

      // Should provide default values for missing or invalid data
      expect(dataFlowPoint.messagesPerSecond, equals(0.0));
      expect(dataFlowPoint.avgProcessingTime, equals(0.0));
      expect(dataFlowPoint.errorRate, equals(0.0));
      // Timestamp should not be null, but will be a current timestamp
      expect(dataFlowPoint.timestamp, isA<DateTime>());
    });
  });
}