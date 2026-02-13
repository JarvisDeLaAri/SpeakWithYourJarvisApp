package ai.bresleveloper.jarvisvoice.network

import okhttp3.*
import okio.ByteString
import okio.ByteString.Companion.toByteString
import org.json.JSONObject
import java.security.SecureRandom
import java.security.cert.X509Certificate
import java.util.concurrent.TimeUnit
import javax.net.ssl.*

class WebSocketClient {
    private var client: OkHttpClient? = null
    private var webSocket: WebSocket? = null

    var onOpen: (() -> Unit)? = null
    var onTextMessage: ((JSONObject) -> Unit)? = null
    var onBinaryMessage: ((ByteArray) -> Unit)? = null
    var onClose: (() -> Unit)? = null
    var onError: ((String) -> Unit)? = null

    fun connect(url: String) {
        // Trust all certs for self-signed support
        val trustManager = object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
            override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
            override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
        }

        val sslContext = SSLContext.getInstance("TLS")
        sslContext.init(null, arrayOf<TrustManager>(trustManager), SecureRandom())

        client = OkHttpClient.Builder()
            .sslSocketFactory(sslContext.socketFactory, trustManager)
            .hostnameVerifier { _, _ -> true }
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(0, TimeUnit.SECONDS)
            .writeTimeout(10, TimeUnit.SECONDS)
            .pingInterval(30, TimeUnit.SECONDS)
            .build()

        val request = Request.Builder().url(url).build()

        webSocket = client?.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                onOpen?.invoke()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    onTextMessage?.invoke(JSONObject(text))
                } catch (e: Exception) {
                    onError?.invoke("Parse error: ${e.message}")
                }
            }

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                onBinaryMessage?.invoke(bytes.toByteArray())
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
                onClose?.invoke()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                onClose?.invoke()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                onError?.invoke(t.message ?: "Connection failed")
                onClose?.invoke()
            }
        })
    }

    fun sendText(json: JSONObject) {
        webSocket?.send(json.toString())
    }

    fun sendBinary(data: ByteArray) {
        webSocket?.send(data.toByteString())
    }

    fun close() {
        webSocket?.close(1000, "hangup")
        webSocket = null
        client?.dispatcher?.executorService?.shutdown()
        client = null
    }
}
