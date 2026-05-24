import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api/auth_api.dart';
import '../core/api/client.dart';
import '../core/models/user.dart';

// ── State ─────────────────────────────────────────────────────────────────────

class AuthState {
  final User? user;
  final bool isLoading;
  final bool isInitialized;

  const AuthState({
    this.user,
    this.isLoading = false,
    this.isInitialized = false,
  });

  bool get isAuthenticated => user != null;

  AuthState copyWith({User? user, bool? isLoading, bool? isInitialized, bool clearUser = false}) =>
      AuthState(
        user: clearUser ? null : (user ?? this.user),
        isLoading: isLoading ?? this.isLoading,
        isInitialized: isInitialized ?? this.isInitialized,
      );
}

// ── Notifier ──────────────────────────────────────────────────────────────────

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState()) {
    _initialize();
  }

  /// On app launch: try to restore session from secure storage
  Future<void> _initialize() async {
    final token = await getStoredToken();
    if (token != null) {
      try {
        final user = await AuthApi.getProfile();
        state = AuthState(user: user, isInitialized: true);
      } catch (_) {
        // Token expired or invalid — clear it
        await deleteToken();
        state = const AuthState(isInitialized: true);
      }
    } else {
      state = const AuthState(isInitialized: true);
    }
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true);
    try {
      final result = await AuthApi.login(email: email, password: password);
      await saveToken(result.accessToken);
      state = AuthState(user: result.user, isInitialized: true);
    } catch (e) {
      state = state.copyWith(isLoading: false);
      rethrow;
    }
  }

  Future<void> register(String email, String password, String displayName) async {
    state = state.copyWith(isLoading: true);
    try {
      final result = await AuthApi.register(
        email: email,
        password: password,
        displayName: displayName,
      );
      await saveToken(result.accessToken);
      state = AuthState(user: result.user, isInitialized: true);
    } catch (e) {
      state = state.copyWith(isLoading: false);
      rethrow;
    }
  }

  Future<void> updateProfile(Map<String, dynamic> data) async {
    final updated = await AuthApi.updateProfile(data);
    state = state.copyWith(user: updated);
  }

  Future<void> logout() async {
    await deleteToken();
    state = const AuthState(isInitialized: true);
  }
}

// ── Provider ──────────────────────────────────────────────────────────────────

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(),
);
