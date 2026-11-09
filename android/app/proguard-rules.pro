# Add project specific ProGuard rules here.
-keepclassmembers class * extends android.webkit.WebViewClient {
   public void *(android.webkit.WebView, java.lang.String);
}
-keepattributes JavascriptInterface
