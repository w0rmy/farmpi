package nz.farmpi.client

internal data class SettingOption(val key: String, val label: String)

internal val EXPLANATION_OPTIONS = listOf(
    SettingOption("simple", "Simple"),
    SettingOption("normal", "Normal"),
    SettingOption("technical", "Technical"),
)

internal val GUIDANCE_OPTIONS = listOf(
    SettingOption("more", "More"),
    SettingOption("normal", "Normal"),
    SettingOption("less", "Less"),
)

internal val TEXT_SIZE_OPTIONS = listOf(
    SettingOption("compact", "Compact"),
    SettingOption("standard", "Standard"),
    SettingOption("large", "Large"),
)
