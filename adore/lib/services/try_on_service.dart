import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:image/image.dart' as img;

import '../utils/constants.dart';

class TryOnResult {
  const TryOnResult(this.bytes);

  final Uint8List bytes;
}

/// Virtual try-on via Magic Hour AI Clothes Changer.
class TryOnService {
  TryOnService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  static const _base = 'https://api.magichour.ai';

  Future<TryOnResult> generate({
    required Uint8List person,
    required Uint8List clothing,
    String garmentType = 'entire_outfit',
  }) async {
    final key = AppConstants.magicHourApiKey;
    if (key.isNotEmpty) {
      return _fromMagicHour(
        key: key,
        person: person,
        clothing: clothing,
        garmentType: garmentType,
      );
    }
    return _fromClothingService(
      person: person,
      clothing: clothing,
      garmentType: garmentType,
    );
  }

  Future<TryOnResult> _fromMagicHour({
    required String key,
    required Uint8List person,
    required Uint8List clothing,
    required String garmentType,
  }) async {
    final personJpeg = _jpeg(person);
    final clothingJpeg = _jpeg(clothing);
    final auth = <String, String>{
      'Authorization': 'Bearer $key',
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };

    final uploadRes = await _client
        .post(
          Uri.parse('$_base/v1/files/upload-urls'),
          headers: auth,
          body: jsonEncode({
            'items': [
              {'type': 'image', 'extension': 'jpg'},
              {'type': 'image', 'extension': 'jpg'},
            ],
          }),
        )
        .timeout(const Duration(seconds: 30));
    if (uploadRes.statusCode != 200) {
      throw TryOnException(_apiMessage(uploadRes.statusCode, uploadRes.body));
    }
    final uploadJson = jsonDecode(uploadRes.body) as Map<String, dynamic>;
    final items = uploadJson['items'];
    if (items is! List || items.length < 2) {
      throw TryOnException('Magic Hour did not return upload links.');
    }
    final personUpload = Map<String, dynamic>.from(items[0] as Map);
    final garmentUpload = Map<String, dynamic>.from(items[1] as Map);
    final personPath = personUpload['file_path'] as String?;
    final garmentPath = garmentUpload['file_path'] as String?;
    final personUrl = personUpload['upload_url'] as String?;
    final garmentUrl = garmentUpload['upload_url'] as String?;
    if (personPath == null ||
        garmentPath == null ||
        personUrl == null ||
        garmentUrl == null) {
      throw TryOnException('Magic Hour did not return upload links.');
    }

    await _putBytes(personUrl, personJpeg);
    await _putBytes(garmentUrl, clothingJpeg);

    final createRes = await _client
        .post(
          Uri.parse('$_base/v1/ai-clothes-changer'),
          headers: auth,
          body: jsonEncode({
            'name': 'Adore virtual try-on',
            'assets': {
              'person_file_path': personPath,
              'garment_file_path': garmentPath,
              'garment_type': garmentType,
            },
          }),
        )
        .timeout(const Duration(seconds: 45));
    if (createRes.statusCode != 200) {
      throw TryOnException(_apiMessage(createRes.statusCode, createRes.body));
    }
    final createJson = jsonDecode(createRes.body) as Map<String, dynamic>;
    final projectId = createJson['id'] as String?;
    if (projectId == null || projectId.isEmpty) {
      throw TryOnException('Magic Hour did not start the try-on.');
    }

    final downloadUrl = await _waitForDownload(key: key, projectId: projectId);
    final imageRes = await _client
        .get(Uri.parse(downloadUrl))
        .timeout(const Duration(seconds: 60));
    if (imageRes.statusCode != 200 || imageRes.bodyBytes.isEmpty) {
      throw TryOnException('Could not download the try-on photo.');
    }
    return TryOnResult(imageRes.bodyBytes);
  }

  Future<void> _putBytes(String url, Uint8List bytes) async {
    final response = await _client
        .put(
          Uri.parse(url),
          headers: {'Content-Type': 'image/jpeg'},
          body: bytes,
        )
        .timeout(const Duration(seconds: 60));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw TryOnException('Could not upload a photo to Magic Hour.');
    }
  }

  Future<String> _waitForDownload({
    required String key,
    required String projectId,
  }) async {
    final deadline = DateTime.now().add(const Duration(minutes: 3));
    while (DateTime.now().isBefore(deadline)) {
      final response = await _client
          .get(
            Uri.parse('$_base/v1/image-projects/$projectId'),
            headers: {
              'Authorization': 'Bearer $key',
              'Accept': 'application/json',
            },
          )
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) {
        throw TryOnException(_apiMessage(response.statusCode, response.body));
      }
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final status = json['status'] as String? ?? '';
      if (status == 'complete') {
        final downloads = json['downloads'];
        if (downloads is List && downloads.isNotEmpty) {
          final first = downloads.first;
          if (first is Map && first['url'] is String) {
            return first['url'] as String;
          }
        }
        throw TryOnException('Magic Hour finished without a try-on photo.');
      }
      if (status == 'error' || status == 'canceled') {
        final error = json['error'];
        final message = error is Map ? error['message'] as String? : null;
        throw TryOnException(
          message?.isNotEmpty == true
              ? message!
              : 'Magic Hour could not create the try-on image.',
        );
      }
      await Future<void>.delayed(const Duration(seconds: 2));
    }
    throw TryOnException('Magic Hour is taking too long. Try again.');
  }

  String _apiMessage(int status, String body) {
    try {
      final json = jsonDecode(body);
      if (json is Map) {
        final message = json['message'];
        if (message is String && message.isNotEmpty) return message;
      }
    } catch (_) {}
    if (status == 401) return 'Magic Hour rejected the API key.';
    if (status == 402) {
      return 'Magic Hour needs more credits. Add credits, then try again.';
    }
    if (status == 429 || status == 503) {
      return 'Magic Hour is busy right now. Try again in a moment.';
    }
    return 'Magic Hour could not create the try-on image. Try again.';
  }

  Uint8List _jpeg(Uint8List bytes) {
    final decoded = img.decodeImage(bytes);
    if (decoded == null) return bytes;
    var picture = decoded;
    // Magic Hour clothes changer max side is 1472px.
    const maxSide = 1400;
    if (picture.width > maxSide || picture.height > maxSide) {
      picture = picture.width >= picture.height
          ? img.copyResize(picture, width: maxSide)
          : img.copyResize(picture, height: maxSide);
    }
    return Uint8List.fromList(img.encodeJpg(picture, quality: 85));
  }

  Future<TryOnResult> _fromClothingService({
    required Uint8List person,
    required Uint8List clothing,
    required String garmentType,
  }) async {
    final uri = Uri.parse('${AppConstants.mlServiceUrl()}/virtual-try-on');
    final request = http.MultipartRequest('POST', uri)
      ..headers.addAll(AppConstants.mlHeaders)
      ..fields['garment_type'] = garmentType
      ..files.add(
        http.MultipartFile.fromBytes('person', person, filename: 'person.jpg'),
      )
      ..files.add(
        http.MultipartFile.fromBytes(
          'clothing',
          clothing,
          filename: 'clothing.jpg',
        ),
      );
    final streamed =
        await _client.send(request).timeout(const Duration(seconds: 180));
    final body = await streamed.stream.bytesToString();
    if (streamed.statusCode != 200) {
      throw TryOnException(_serviceMessage(streamed.statusCode, body));
    }
    final json = jsonDecode(body) as Map<String, dynamic>;
    final encoded = json['imageBase64'] as String?;
    if (encoded == null || encoded.isEmpty) {
      throw TryOnException('Magic Hour finished without a try-on photo.');
    }
    return TryOnResult(base64Decode(encoded));
  }

  String _serviceMessage(int status, String body) {
    try {
      final json = jsonDecode(body);
      final detail = json is Map ? json['detail'] : null;
      if (detail is String && detail.isNotEmpty) return detail;
    } catch (_) {}
    if (status == 503) {
      return 'The clothing service is missing the Magic Hour API key.';
    }
    return 'Could not reach the try-on service. Start it on ngrok, then try again.';
  }
}

class TryOnException implements Exception {
  TryOnException(this.message);

  final String message;
}
