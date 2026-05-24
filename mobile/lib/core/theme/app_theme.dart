import 'package:flutter/material.dart';

// ── Colour palette (mirrors Tailwind tokens in globals.css) ──────────────────

const _background = Color(0xFF0A0A0A);
const _surface = Color(0xFF141414);
const _surfaceElevated = Color(0xFF1C1C1C);
const _border = Color(0xFF262626);

const _textPrimary = Color(0xFFEDEDED);
const _textSecondary = Color(0xFF9B9B9B);
const _textMuted = Color(0xFF6B6B6B);

const _emerald = Color(0xFF10B981);
const _emeraldDark = Color(0xFF059669);
const _emeraldLight = Color(0xFF34D399);

const _red = Color(0xFFF87171);
const _amber = Color(0xFFFBBF24);
const _blue = Color(0xFF60A5FA);
const _purple = Color(0xFFA78BFA);

// ── Theme ─────────────────────────────────────────────────────────────────────

class AppTheme {
  AppTheme._();

  static ThemeData get dark => ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: _background,
        colorScheme: const ColorScheme.dark(
          primary: _emerald,
          secondary: _emeraldLight,
          surface: _surface,
          onPrimary: Colors.white,
          onSecondary: Colors.white,
          onSurface: _textPrimary,
          error: _red,
        ),
        cardTheme: const CardThemeData(
          color: _surface,
          surfaceTintColor: Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(16)),
            side: BorderSide(color: _border, width: 1),
          ),
          elevation: 0,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: _surface,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: _border),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: _border),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: _emerald.withAlpha(127)),
          ),
          labelStyle: const TextStyle(color: _textSecondary, fontSize: 14),
          hintStyle: const TextStyle(color: _textMuted, fontSize: 14),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: _emerald,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
            textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
            elevation: 0,
          ),
        ),
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(foregroundColor: _emerald),
        ),
        dividerTheme: const DividerThemeData(color: _border, thickness: 1),
        bottomNavigationBarTheme: const BottomNavigationBarThemeData(
          backgroundColor: _surface,
          selectedItemColor: _emerald,
          unselectedItemColor: _textMuted,
          type: BottomNavigationBarType.fixed,
          elevation: 0,
        ),
        textTheme: const TextTheme(
          displayLarge: TextStyle(color: _textPrimary, fontWeight: FontWeight.bold),
          displayMedium: TextStyle(color: _textPrimary, fontWeight: FontWeight.bold),
          headlineLarge: TextStyle(color: _textPrimary, fontWeight: FontWeight.bold, fontSize: 24),
          headlineMedium: TextStyle(color: _textPrimary, fontWeight: FontWeight.w600, fontSize: 20),
          headlineSmall: TextStyle(color: _textPrimary, fontWeight: FontWeight.w600, fontSize: 18),
          titleLarge: TextStyle(color: _textPrimary, fontWeight: FontWeight.w600, fontSize: 16),
          titleMedium: TextStyle(color: _textPrimary, fontWeight: FontWeight.w500, fontSize: 14),
          bodyLarge: TextStyle(color: _textPrimary, fontSize: 16),
          bodyMedium: TextStyle(color: _textPrimary, fontSize: 14),
          bodySmall: TextStyle(color: _textSecondary, fontSize: 12),
          labelLarge: TextStyle(color: _textPrimary, fontWeight: FontWeight.w500, fontSize: 14),
        ),
      );
}

// ── Colour access helpers ─────────────────────────────────────────────────────

class AppColors {
  AppColors._();

  static const background = _background;
  static const surface = _surface;
  static const surfaceElevated = _surfaceElevated;
  static const border = _border;
  static const textPrimary = _textPrimary;
  static const textSecondary = _textSecondary;
  static const textMuted = _textMuted;
  static const emerald = _emerald;
  static const emeraldDark = _emeraldDark;
  static const emeraldLight = _emeraldLight;
  static const red = _red;
  static const amber = _amber;
  static const blue = _blue;
  static const purple = _purple;
}
