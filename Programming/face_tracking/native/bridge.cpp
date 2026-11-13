// Uses SDK headers for ABI correctness; no NVIDIA code or model redistribution.
#include <windows.h>
#include <nvAR.h>
#include <nvCVImage.h>
#include <array>
#include <cstdint>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <string>

#define API extern "C" __declspec(dllexport)
static thread_local std::string last_error;
static void check(int status, const char* operation) {
    if (status) throw std::runtime_error(std::string(operation) + " failed, NVIDIA status " + std::to_string(status));
}
template<class T> T symbol(HMODULE library, const char* name) {
    auto pointer = GetProcAddress(library, name);
    if (!pointer) throw std::runtime_error(std::string("Missing SDK export: ") + name);
    return reinterpret_cast<T>(pointer);
}
#define FUNCTION(name) decltype(&name) p_##name = nullptr
#define LOAD(module, name) p_##name = symbol<decltype(&name)>(module, #name)

struct Tracker {
    HMODULE ar = nullptr, cv = nullptr, cuda = nullptr;
    NvAR_FeatureHandle feature = nullptr;
    CUstream stream = nullptr;
    // Raw descriptor storage avoids C++ constructors/destructors in nvCVImage.h.
    alignas(NvCVImage) unsigned char image_storage[sizeof(NvCVImage)]{};
    std::array<NvAR_Point2f, 68> landmarks{};
    std::array<float, 68> confidence{};
    std::array<NvAR_Rect, 1> rects{};
    NvAR_BBoxes boxes{};
    FUNCTION(NvAR_Create); FUNCTION(NvAR_Destroy); FUNCTION(NvAR_Load);
    FUNCTION(NvAR_Run); FUNCTION(NvAR_SetU32); FUNCTION(NvAR_SetString);
    FUNCTION(NvAR_SetObject); FUNCTION(NvAR_SetF32Array); FUNCTION(NvAR_SetCudaStream);
    FUNCTION(NvCVImage_Init);
    using Synchronize = int (WINAPI *)(CUstream);
    Synchronize sync = nullptr;
    ~Tracker() {
        if (stream && sync) sync(stream);
        if (feature && p_NvAR_Destroy) p_NvAR_Destroy(feature);
        if (ar) FreeLibrary(ar);
        if (cv) FreeLibrary(cv);
        if (cuda) FreeLibrary(cuda);
    }
    void init(const wchar_t* sdk, const char* models, uintptr_t stream_pointer, int quality) {
        const std::wstring root(sdk);
        constexpr auto flags = LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS;
        ar = LoadLibraryExW((root + L"/nvARPose.dll").c_str(), nullptr, flags);
        cv = LoadLibraryExW((root + L"/NVCVImage.dll").c_str(), nullptr, flags);
        cuda = LoadLibraryW(L"nvcuda.dll");
        if (!ar || !cv || !cuda) throw std::runtime_error("Cannot load Maxine DLLs/dependencies; Windows error " + std::to_string(GetLastError()));
        LOAD(ar, NvAR_Create); LOAD(ar, NvAR_Destroy); LOAD(ar, NvAR_Load);
        LOAD(ar, NvAR_Run); LOAD(ar, NvAR_SetU32); LOAD(ar, NvAR_SetString);
        LOAD(ar, NvAR_SetObject); LOAD(ar, NvAR_SetF32Array); LOAD(ar, NvAR_SetCudaStream);
        LOAD(cv, NvCVImage_Init);
        sync = symbol<Synchronize>(cuda, "cuStreamSynchronize");
        stream = reinterpret_cast<CUstream>(stream_pointer);
        check(p_NvAR_Create(NvAR_Feature_LandmarkDetection, &feature), "NvAR_Create");
        check(p_NvAR_SetString(feature, NvAR_Parameter_Config(ModelDir), models), "ModelDir");
        check(p_NvAR_SetCudaStream(feature, NvAR_Parameter_Config(CUDAStream), stream), "CUDAStream");
        check(p_NvAR_SetU32(feature, NvAR_Parameter_Config(BatchSize), 1), "BatchSize");
        check(p_NvAR_SetU32(feature, NvAR_Parameter_Config(Landmarks_Size), 68), "Landmarks_Size");
        check(p_NvAR_SetU32(feature, NvAR_Parameter_Config(Temporal), 1), "Temporal");
        check(p_NvAR_SetU32(feature, NvAR_Parameter_Config(Mode), quality), "Mode");
        boxes.boxes = rects.data();
        boxes.max_boxes = 1;
        check(p_NvAR_SetObject(feature, NvAR_Parameter_Output(Landmarks), landmarks.data(), sizeof(NvAR_Point2f)), "Landmarks");
        check(p_NvAR_SetF32Array(feature, NvAR_Parameter_Output(LandmarksConfidence), confidence.data(), 68), "LandmarksConfidence");
        check(p_NvAR_SetObject(feature, NvAR_Parameter_Output(BoundingBoxes), &boxes, sizeof(boxes)), "BoundingBoxes");
        check(p_NvAR_Load(feature), "NvAR_Load");
    }
};

API unsigned ft_abi_version() { return 1; }
API const char* ft_error() { return last_error.c_str(); }
API void* ft_create(const wchar_t* sdk, const char* models, uintptr_t stream, int quality) {
    try {
        auto tracker = std::make_unique<Tracker>();
        tracker->init(sdk, models, stream, quality);
        return tracker.release();
    } catch (const std::exception& error) { last_error = error.what(); return nullptr; }
}
API void ft_destroy(void* handle) { delete static_cast<Tracker*>(handle); }
API int ft_run(void* handle, uintptr_t pixels, unsigned width, unsigned height,
               unsigned pitch, float* xy, float* confidence, float* box) {
    try {
        if (!handle || !pixels || !width || !height || pitch < width * 3) throw std::runtime_error("Invalid GPU image");
        auto& t = *static_cast<Tracker*>(handle);
        auto* image = reinterpret_cast<NvCVImage*>(t.image_storage);
        check(t.p_NvCVImage_Init(image, width, height, pitch, reinterpret_cast<void*>(pixels),
                                NVCV_BGR, NVCV_U8, NVCV_CHUNKY, NVCV_GPU), "NvCVImage_Init");
        check(t.p_NvAR_SetObject(t.feature, NvAR_Parameter_Input(Image), image, sizeof(NvCVImage)), "Input image");
        t.confidence.fill(0);
        t.landmarks.fill({});
        t.boxes.num_boxes = 0;
        check(t.p_NvAR_Run(t.feature), "NvAR_Run");
        check(t.sync(t.stream), "cuStreamSynchronize");
        for (size_t i = 0; i < 68; ++i) {
            xy[2*i] = t.landmarks[i].x; xy[2*i+1] = t.landmarks[i].y;
            confidence[i] = t.confidence[i];
        }
        if (!t.boxes.num_boxes) return 0;
        box[0] = t.rects[0].x; box[1] = t.rects[0].y;
        box[2] = t.rects[0].width; box[3] = t.rects[0].height;
        return 1;
    } catch (const std::exception& error) { last_error = error.what(); return -1; }
}
