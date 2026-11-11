package pw.dario10.dieta

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.view.View
import android.webkit.*
import android.widget.Button
import android.widget.ProgressBar
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import java.io.File

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var swipeRefreshLayout: SwipeRefreshLayout
    private lateinit var progressBar: ProgressBar
    private lateinit var layoutOffline: View
    private lateinit var btnRetry: Button

    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private var cameraPhotoUri: Uri? = null

    private val defaultUrl: String
        get() = getString(R.string.default_url)

    private val requestPermissionsLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { _ -> }

    private val cameraChooserLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            var results: Array<Uri>? = null
            if (result.resultCode == RESULT_OK) {
                val data = result.data
                results = when {
                    data?.clipData != null -> {
                        val count = data.clipData!!.itemCount
                        Array(count) { i -> data.clipData!!.getItemAt(i).uri }
                    }
                    data?.data != null -> arrayOf(data.data!!)
                    cameraPhotoUri != null -> {
                        // Check if file was written
                        try {
                            arrayOf(cameraPhotoUri!!)
                        } catch (e: Exception) {
                            null
                        }
                    }
                    else -> null
                }
            }
            filePathCallback?.onReceiveValue(results)
            filePathCallback = null
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        swipeRefreshLayout = findViewById(R.id.swipeRefreshLayout)
        progressBar = findViewById(R.id.progressBar)
        layoutOffline = findViewById(R.id.layoutOffline)
        btnRetry = findViewById(R.id.btnRetry)

        checkPermissions()
        setupWebView()
        setupSwipeRefresh()
        setupBackNavigation()
        setupRetryButton()

        loadAppUrl()
    }

    private fun checkPermissions() {
        val needed = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.RECORD_AUDIO)
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.CAMERA)
        }
        if (needed.isNotEmpty()) {
            requestPermissionsLauncher.launch(needed.toTypedArray())
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        webView.apply {
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                databaseEnabled = true
                cacheMode = WebSettings.LOAD_DEFAULT
                allowFileAccess = false
                allowContentAccess = true
                loadsImagesAutomatically = true
                mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
                userAgentString = "${settings.userAgentString} NutriXApp/1.1.0 (Android)"
            }

            val cookieManager = CookieManager.getInstance()
            cookieManager.setAcceptCookie(true)
            cookieManager.setAcceptThirdPartyCookies(this, true)

            webViewClient = object : WebViewClient() {
                override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                    super.onPageStarted(view, url, favicon)
                    progressBar.visibility = View.VISIBLE
                    layoutOffline.visibility = View.GONE
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    super.onPageFinished(view, url)
                    progressBar.visibility = View.GONE
                    swipeRefreshLayout.isRefreshing = false
                }

                override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                    super.onReceivedError(view, request, error)
                    if (request?.isForMainFrame == true) {
                        showOfflineLayout()
                    }
                }
            }

            webChromeClient = object : WebChromeClient() {
                override fun onPermissionRequest(request: PermissionRequest?) {
                    request?.grant(request.resources)
                }

                override fun onShowFileChooser(
                    wv: WebView?,
                    fpc: ValueCallback<Array<Uri>>?,
                    params: FileChooserParams?
                ): Boolean {
                    filePathCallback?.onReceiveValue(null)
                    filePathCallback = fpc

                    // 1. Prepare Camera Intent with temporary file
                    var cameraIntent: Intent? = null
                    try {
                        val photoFile = File.createTempFile("meal_photo_", ".jpg", cacheDir)
                        cameraPhotoUri = FileProvider.getUriForFile(
                            this@MainActivity,
                            "${applicationContext.packageName}.fileprovider",
                            photoFile
                        )
                        cameraIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE).apply {
                            putExtra(MediaStore.EXTRA_OUTPUT, cameraPhotoUri)
                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
                        }
                    } catch (e: Exception) {
                        cameraPhotoUri = null
                    }

                    // 2. Prepare Gallery / File Picker Intent
                    val contentIntent = Intent(Intent.ACTION_GET_CONTENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = "image/*"
                    }

                    // 3. Determine if direct camera or chooser with both options
                    val isDirectCapture = params?.isCaptureEnabled == true

                    if (isDirectCapture && cameraIntent != null) {
                        cameraChooserLauncher.launch(cameraIntent)
                    } else {
                        val chooserIntent = Intent(Intent.ACTION_CHOOSER).apply {
                            putExtra(Intent.EXTRA_INTENT, contentIntent)
                            putExtra(Intent.EXTRA_TITLE, "Tomar foto con Cámara o seleccionar de Galería")
                            if (cameraIntent != null) {
                                putExtra(Intent.EXTRA_INITIAL_INTENTS, arrayOf(cameraIntent))
                            }
                        }
                        cameraChooserLauncher.launch(chooserIntent)
                    }
                    return true
                }
            }
        }
    }

    private fun setupSwipeRefresh() {
        swipeRefreshLayout.setColorSchemeResources(R.color.accent, R.color.primary)
        swipeRefreshLayout.setOnRefreshListener {
            webView.reload()
        }
    }

    private fun setupBackNavigation() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                webView.evaluateJavascript(
                    "(function(){var openDlgs=Array.prototype.slice.call(document.querySelectorAll('dialog[open]'));if(openDlgs.length){openDlgs[openDlgs.length-1].close('cancel');return true;}return false;})()"
                ) { result ->
                    if (result == "true") {
                        return@evaluateJavascript
                    }
                    if (webView.canGoBack()) {
                        webView.goBack()
                    } else {
                        finish()
                    }
                }
            }
        })
    }

    private fun setupRetryButton() {
        btnRetry.setOnClickListener {
            layoutOffline.visibility = View.GONE
            loadAppUrl()
        }
    }

    private fun loadAppUrl() {
        if (!isOnline()) {
            showOfflineLayout()
            return
        }
        webView.loadUrl(defaultUrl)
    }

    private fun showOfflineLayout() {
        progressBar.visibility = View.GONE
        swipeRefreshLayout.isRefreshing = false
        layoutOffline.visibility = View.VISIBLE
    }

    private fun isOnline(): Boolean {
        val connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }
}
