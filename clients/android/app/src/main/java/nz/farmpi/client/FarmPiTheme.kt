package nz.farmpi.client

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp

internal val FarmPiGreen = Color(0xFF2F7D32)
internal val FarmPiGreenStrong = Color(0xFF1F6526)
internal val FarmPiGreenSoft = Color(0xFFE8F5E9)
internal val FarmPiBackground = Color(0xFFF6F8F5)
internal val FarmPiSurface = Color(0xFFFFFFFF)
internal val FarmPiSurfaceMuted = Color(0xFFF0F3F1)
internal val FarmPiText = Color(0xFF1E2420)
internal val FarmPiTextMuted = Color(0xFF657068)
internal val FarmPiOutline = Color(0xFFD8DED9)
internal val FarmPiAmber = Color(0xFFE2A400)
internal val FarmPiAmberSoft = Color(0xFFFFF4D6)
internal val FarmPiRed = Color(0xFFD64545)
internal val FarmPiRedSoft = Color(0xFFFDEBEC)
internal val FarmPiBlue = Color(0xFF3C78B8)
internal val FarmPiBlueSoft = Color(0xFFEAF2FA)
internal val FarmPiGrey = Color(0xFF6F7772)
internal val FarmPiGreySoft = Color(0xFFF0F2F1)

private val FarmPiColours = lightColorScheme(
    primary = FarmPiGreen,
    onPrimary = Color.White,
    primaryContainer = FarmPiGreenSoft,
    onPrimaryContainer = FarmPiGreenStrong,
    secondary = Color(0xFF5A6D5E),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFEAF0EA),
    onSecondaryContainer = FarmPiText,
    tertiary = FarmPiBlue,
    onTertiary = Color.White,
    tertiaryContainer = FarmPiBlueSoft,
    onTertiaryContainer = Color(0xFF244D76),
    background = FarmPiBackground,
    onBackground = FarmPiText,
    surface = FarmPiSurface,
    onSurface = FarmPiText,
    surfaceVariant = FarmPiSurfaceMuted,
    onSurfaceVariant = FarmPiTextMuted,
    outline = FarmPiOutline,
    outlineVariant = Color(0xFFE8ECE9),
    error = FarmPiRed,
    onError = Color.White,
    errorContainer = FarmPiRedSoft,
    onErrorContainer = Color(0xFF7A2222),
)

@Composable
internal fun FarmPiTheme(displayDensity: String, content: @Composable () -> Unit) {
    val density = LocalDensity.current
    val fontScale = when (displayDensity) {
        "compact" -> 0.90f
        "large" -> 1.25f
        else -> 1.0f
    }
    CompositionLocalProvider(LocalDensity provides Density(density.density, density.fontScale * fontScale)) {
        MaterialTheme(
            colorScheme = FarmPiColours,
            shapes = Shapes(
                small = RoundedCornerShape(10.dp),
                medium = RoundedCornerShape(16.dp),
                large = RoundedCornerShape(22.dp),
            ),
            content = content,
        )
    }
}

internal data class FarmPiStatusPalette(val foreground: Color, val background: Color)

internal fun farmPiStatusPalette(text: String): FarmPiStatusPalette {
    val value = text.lowercase()
    return when {
        "missing" in value || "failed" in value || "error" in value || "unavailable" in value ->
            FarmPiStatusPalette(FarmPiRed, FarmPiRedSoft)
        "old" in value || "stale" in value || "pending" in value || "attention" in value ->
            FarmPiStatusPalette(Color(0xFF8A6500), FarmPiAmberSoft)
        "current" in value || "online" in value || "in sync" in value || "reporting" in value || "connected" in value || value == "live" ->
            FarmPiStatusPalette(FarmPiGreenStrong, FarmPiGreenSoft)
        "simulated" in value || "prototype" in value || "coming later" in value ->
            FarmPiStatusPalette(Color(0xFF2C5F93), FarmPiBlueSoft)
        else ->
            FarmPiStatusPalette(FarmPiGrey, FarmPiGreySoft)
    }
}
