import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:track/app.dart';

void main() {
  testWidgets('App smoke test — renders without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: TrackApp()));
    // Just verify it boots — full tests live in integration_test/
    await tester.pump();
  });
}
