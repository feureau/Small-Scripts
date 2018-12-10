using UnityEngine;

public class Script_MaintainAspectRatio : MonoBehaviour {
    // Use this for initialization
    [SerializeField]
    private float horizontalFOV = 103.0f;

    [SerializeField]
    private float targetHorizontalAspectRatio = 16.0f;
    [SerializeField]
    private float targetVerticalAspectRatio = 9.0f;

    [SerializeField]
    bool enableLetterboxing = false;

    //[SerializeField]
    //bool enableMaxAspectRatioLimiterLetterboxing = false;

    float hFOVrad = 0.0f, camH = 0.0f, vFOVrad = 0.0f;

    private void SetVerticalFOV(float hFOV) {
        float targetAspect = targetHorizontalAspectRatio / targetVerticalAspectRatio; // set the desired aspect ratio

        // current viewport height should be scaled by this amount
        float scaleHeight = GetComponent<Camera>().aspect / targetAspect;

        if (enableLetterboxing) {// maintain aspect ratio with letterboxing.
            float windowaspect = (float)Screen.width / (float)Screen.height;
            scaleHeight = windowaspect / targetAspect;
            Camera camera = GetComponent<Camera>();

            if (scaleHeight < 1.0f) {
                Rect rect = camera.rect;

                rect.width = 1.0f;
                rect.height = scaleHeight;
                rect.x = 0;
                rect.y = (1.0f - scaleHeight) / 2.0f;

                camera.rect = rect;
            }
            else // add pillarbox
            {
                float scalewidth = 1.0f / scaleHeight;

                Rect rect = camera.rect;

                rect.width = scalewidth;
                rect.height = 1.0f;
                rect.x = (1.0f - scalewidth) / 2.0f;
                rect.y = 0;

                camera.rect = rect;
            }
        }
        else { // maintain aspect ratio without letterboxing.
            if (scaleHeight <= 1.0f) {
                hFOVrad = hFOV * Mathf.Deg2Rad;
                camH = Mathf.Tan(hFOVrad * 0.5f) / GetComponent<Camera>().aspect;
                vFOVrad = Mathf.Atan(camH) * 2;
                GetComponent<Camera>().fieldOfView = vFOVrad * Mathf.Rad2Deg;
                //print("VFOV" + GetComponent<Camera>().fieldOfView);
            }
            else if (scaleHeight > 1.0f) {
                hFOVrad = hFOV * Mathf.Deg2Rad;
                camH = Mathf.Tan(hFOVrad * 0.5f) / targetAspect;
                vFOVrad = Mathf.Atan(camH) * 2;
                GetComponent<Camera>().fieldOfView = vFOVrad * Mathf.Rad2Deg;
                //print("VFOV" + GetComponent<Camera>().fieldOfView);
            }
        }
    }
    private void Start() {
        SetVerticalFOV(horizontalFOV);
    }
    // Update is called once per frame
    private void Update() {
    }
}