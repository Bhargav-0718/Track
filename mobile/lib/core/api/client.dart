import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

// ── Constants ─────────────────────────────────────────────────────────────────

/// Base URL switches automatically:
///   Web (Chrome dev)   → localhost:8000 (same machine)
///   Android emulator   → 10.0.2.2:8000 (emulator loopback to host)
///   Physical device    → change to your LAN IP e.g. http://192.168.1.X:8000
///   Production         → https://api.trackapp.in
final String _baseUrl = kIsWeb ? 'http://localhost:8000' : 'http://10.0.2.2:8000';

const String _tokenKey = 'track_token';

// ── Storage ───────────────────────────────────────────────────────────────────

final _storage = FlutterSecureStorage(
  aOptions: const AndroidOptions(encryptedSharedPreferences: true),
);

Future<String?> getStoredToken() => _storage.read(key: _tokenKey);
Future<void> saveToken(String token) => _storage.write(key: _tokenKey, value: token);
Future<void> deleteToken() => _storage.delete(key: _tokenKey);

// ── ApiError ──────────────────────────────────────────────────────────────────

class ApiError implements Exception {
  final int statusCode;
  final String message;
  final dynamic details;

  const ApiError({required this.statusCode, required this.message, this.details});

  @override
  String toString() => 'ApiError($statusCode): $message';
}

// ── Dio client factory ────────────────────────────────────────────────────────

Dio createDio() {
  final dio = Dio(
    BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      contentType: 'application/json',
    ),
  );

  // Auth interceptor — attach Bearer token to every request
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await getStoredToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) {
        final response = error.response;
        if (response != null) {
          final data = response.data;
          String message = 'HTTP ${response.statusCode}';
          if (data is Map) {
            message = (data['message'] ?? data['detail'] ?? message).toString();
            // FastAPI 422 detail is a list — grab first message
            if (data['detail'] is List) {
              final list = data['detail'] as List;
              if (list.isNotEmpty) {
                final first = list.first;
                if (first is Map && first['msg'] != null) {
                  message = first['msg'].toString();
                }
              }
            }
          }
          return handler.reject(
            DioException(
              requestOptions: error.requestOptions,
              response: response,
              error: ApiError(
                statusCode: response.statusCode ?? 0,
                message: message,
                details: data,
              ),
            ),
          );
        }
        return handler.next(error);
      },
    ),
  );

  return dio;
}

// ── Singleton ─────────────────────────────────────────────────────────────────

final dio = createDio();

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Extracts [ApiError] from a [DioException] (thrown by the interceptor above).
ApiError extractApiError(Object err) {
  if (err is DioException && err.error is ApiError) return err.error as ApiError;
  if (err is ApiError) return err;
  return ApiError(statusCode: 0, message: err.toString());
}
