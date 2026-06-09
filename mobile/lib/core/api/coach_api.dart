import 'dart:async';
import 'dart:convert';
import 'dart:io' as io;

import 'client.dart';

class CoachMessage {
  final String role; // 'user' | 'assistant'
  final String content;
  final DateTime createdAt;

  const CoachMessage({
    required this.role,
    required this.content,
    required this.createdAt,
  });

  factory CoachMessage.fromJson(Map<String, dynamic> json) => CoachMessage(
        role: json['role'] as String,
        content: json['content'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}

class CoachApi {
  const CoachApi._();

  /// Fetch conversation history.
  static Future<List<CoachMessage>> getHistory() async {
    final response =
        await dio.get<Map<String, dynamic>>('/api/v1/coach/history');
    final msgs = response.data!['messages'] as List<dynamic>;
    return msgs
        .map((e) => CoachMessage.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Clear conversation history.
  static Future<void> clearHistory() async {
    await dio.delete('/api/v1/coach/history');
  }

  /// Stream a chat response via SSE.
  ///
  /// Each yielded string is a raw JSON payload from a `data:` line.
  /// Event types: text_delta, food_logged, workout_logged, steps_logged, done, error.
  static Stream<String> chat(String message) {
    final controller = StreamController<String>();
    _streamChat(message, controller);
    return controller.stream;
  }

  static Future<void> _streamChat(
    String message,
    StreamController<String> controller,
  ) async {
    final token = await getStoredToken();
    final baseUrl = dio.options.baseUrl;
    final httpClient = io.HttpClient();
    httpClient.connectionTimeout = const Duration(seconds: 15);

    try {
      final request = await httpClient
          .postUrl(Uri.parse('$baseUrl/api/v1/coach/chat'));
      request.headers.set(io.HttpHeaders.contentTypeHeader, 'application/json');
      request.headers.set(io.HttpHeaders.acceptHeader, 'text/event-stream');
      if (token != null) {
        request.headers.set(io.HttpHeaders.authorizationHeader, 'Bearer $token');
      }
      request.write(jsonEncode({'message': message}));

      final response = await request.close();
      await response
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .forEach((line) {
        if (line.startsWith('data: ')) {
          controller.add(line.substring(6).trim());
        }
      });
      controller.close();
    } catch (e) {
      controller.addError(e);
    } finally {
      httpClient.close();
    }
  }
}
