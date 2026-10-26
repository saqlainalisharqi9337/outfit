import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import '../models/user_model.dart';
import '../models/wardrobe_item.dart';
import '../services/storage_service.dart';
import '../services/wardrobe_service.dart';
import '../utils/enums.dart';
import '../utils/exceptions.dart';

class WardrobeProvider extends ChangeNotifier {
  WardrobeProvider({
    required WardrobeService wardrobeService,
    required StorageService storageService,
  })  : _wardrobeService = wardrobeService,
        _storageService = storageService;

  final WardrobeService _wardrobeService;
  final StorageService _storageService;
  final _uuid = const Uuid();

  List<WardrobeItem> items = [];
  bool loading = false;
  String? error;
  double? uploadProgress;
  ClothingCategory? filter;

  List<WardrobeItem> get visible {
    if (filter == null) return items;
    return items.where((i) => i.category == filter).toList();
  }

  void bind(String uid) {
    _wardrobeService.watch(uid).listen((value) {
      items = value;
      notifyListeners();
    }, onError: (e) {
      error = 'Could not load your wardrobe.';
      notifyListeners();
    });
  }

  void setFilter(ClothingCategory? category) {
    filter = category;
    notifyListeners();
  }

  Future<WardrobeItem> addItem({
    required UserModel user,
    required Uint8List imageBytes,
    required WardrobeItem draft,
  }) async {
    error = null;
    uploadProgress = 0;
    notifyListeners();
    try {
      final url = await _storageService.uploadWardrobeImage(
        uid: user.id,
        bytes: imageBytes,
        onProgress: (p) {
          uploadProgress = p;
          notifyListeners();
        },
      );
      final item = draft.copyWith(imageUrl: url);
      final saved = WardrobeItem(
        itemId: draft.itemId.isEmpty ? _uuid.v4() : draft.itemId,
        userId: user.id,
        imageUrl: url,
        category: item.category,
        subcategory: item.subcategory,
        color: item.color,
        secondaryColor: item.secondaryColor,
        pattern: item.pattern,
        material: item.material,
        style: item.style,
        seasons: item.seasons,
        formality: item.formality,
        cultureCompatibility: item.cultureCompatibility,
        weatherSuitability: item.weatherSuitability,
        occasions: item.occasions,
        aiConfidence: draft.aiConfidence,
        createdAt: DateTime.now(),
      );
      await _wardrobeService.upsert(saved);
      return saved;
    } on AppException catch (e) {
      error = e.message;
      rethrow;
    } finally {
      uploadProgress = null;
      notifyListeners();
    }
  }

  Future<void> updateItem(WardrobeItem item) async {
    await _wardrobeService.upsert(item);
  }

  Future<void> deleteItem(WardrobeItem item) async {
    await _wardrobeService.delete(item.userId, item.itemId);
    if (item.imageUrl.isNotEmpty) {
      await _storageService.deleteByUrl(item.imageUrl);
    }
  }
}
