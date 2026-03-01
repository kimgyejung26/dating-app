import 'package:flutter/cupertino.dart';
import 'package:url_launcher/url_launcher.dart';

Future<void> openGmailApp(BuildContext context) async {
  final gmailUri = Uri.parse('googlegmail://');

  try {
    if (await canLaunchUrl(gmailUri)) {
      await launchUrl(gmailUri, mode: LaunchMode.externalApplication);
      return;
    }
  } catch (_) {}

  final mailto = Uri.parse('mailto:');
  if (await canLaunchUrl(mailto)) {
    await launchUrl(mailto, mode: LaunchMode.externalApplication);
    return;
  }

  if (context.mounted) {
    await showCupertinoDialog<void>(
      context: context,
      builder: (_) => const CupertinoAlertDialog(
        title: Text('메일 앱을 열 수 없음'),
        content: Text('직접 Gmail 또는 메일 앱을 열어주세요.'),
        actions: [
          CupertinoDialogAction(child: Text('확인')),
        ],
      ),
    );
  }
}
