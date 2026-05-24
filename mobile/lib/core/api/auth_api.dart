import '../models/user.dart';
import 'client.dart';

class AuthApi {
  const AuthApi._();

  static Future<({String accessToken, User user})> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/api/v1/auth/register',
      data: {'email': email, 'password': password, 'display_name': displayName},
    );
    final data = response.data!;
    return (
      accessToken: data['access_token'] as String,
      user: User.fromJson(data['user'] as Map<String, dynamic>),
    );
  }

  static Future<({String accessToken, User user})> login({
    required String email,
    required String password,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/api/v1/auth/login',
      data: {'email': email, 'password': password},
    );
    final data = response.data!;
    return (
      accessToken: data['access_token'] as String,
      user: User.fromJson(data['user'] as Map<String, dynamic>),
    );
  }

  static Future<User> getProfile() async {
    final response = await dio.get<Map<String, dynamic>>('/api/v1/users/me');
    return User.fromJson(response.data!);
  }

  static Future<User> updateProfile(Map<String, dynamic> data) async {
    final response = await dio.put<Map<String, dynamic>>('/api/v1/users/me', data: data);
    return User.fromJson(response.data!);
  }
}
