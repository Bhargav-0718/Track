import 'dart:io';

import 'package:dio/dio.dart';

import 'client.dart';

class ProgressCheckpoint {
  final String id;
  final String checkpointDate;
  final double? weightKg;
  final double? bodyFatPercentage;
  final String? notes;
  final List<String> tags;
  final int photoCount;
  final String? primaryPhotoUrl;
  final DateTime createdAt;

  const ProgressCheckpoint({
    required this.id,
    required this.checkpointDate,
    this.weightKg,
    this.bodyFatPercentage,
    this.notes,
    required this.tags,
    required this.photoCount,
    this.primaryPhotoUrl,
    required this.createdAt,
  });

  factory ProgressCheckpoint.fromJson(Map<String, dynamic> json) =>
      ProgressCheckpoint(
        id: json['id'] as String,
        checkpointDate: json['checkpoint_date'] as String,
        weightKg: (json['weight_kg'] as num?)?.toDouble(),
        bodyFatPercentage:
            (json['body_fat_percentage'] as num?)?.toDouble(),
        notes: json['notes'] as String?,
        tags: (json['tags'] as List<dynamic>).cast<String>(),
        photoCount: json['photo_count'] as int? ?? 0,
        primaryPhotoUrl: json['primary_photo_url'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}

class ProgressApi {
  const ProgressApi._();

  static Future<List<ProgressCheckpoint>> getCheckpoints({
    int page = 1,
    int pageSize = 20,
  }) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/api/v1/progress/checkpoints/',
      queryParameters: {'page': page, 'page_size': pageSize},
    );
    final items = response.data!['items'] as List<dynamic>;
    return items
        .map((e) => ProgressCheckpoint.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  static Future<ProgressCheckpoint> createCheckpoint({
    required String date,
    double? weightKg,
    double? bodyFatPercentage,
    String? notes,
    List<String> tags = const [],
    List<File> photos = const [],
  }) async {
    // Step 1: create the checkpoint record
    final response = await dio.post<Map<String, dynamic>>(
      '/api/v1/progress/checkpoints/',
      data: {
        'checkpoint_date': date,
        if (weightKg != null) 'weight_kg': weightKg,
        if (bodyFatPercentage != null)
          'body_fat_percentage': bodyFatPercentage,
        if (notes != null) 'notes': notes,
        'tags': tags,
      },
    );
    final checkpoint = ProgressCheckpoint.fromJson(response.data!);

    // Step 2: upload photos if any
    if (photos.isNotEmpty) {
      for (int i = 0; i < photos.length; i++) {
        final formData = FormData.fromMap({
          'file': await MultipartFile.fromFile(
            photos[i].path,
            filename: 'photo_$i.jpg',
          ),
          'display_order': i,
        });
        try {
          await dio.post<void>(
            '/api/v1/progress/checkpoints/${checkpoint.id}/photos/',
            data: formData,
          );
        } catch (_) {
          // Non-fatal: checkpoint created even if photo upload fails
        }
      }
    }

    return checkpoint;
  }

  static Future<void> deleteCheckpoint(String id) async {
    await dio.delete('/api/v1/progress/checkpoints/$id/');
  }
}
