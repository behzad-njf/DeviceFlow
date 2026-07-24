package ir.behzaaad.deviceflow.agent.ui.help

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import ir.behzaaad.deviceflow.agent.R

enum class HelpTopic {
    GettingStarted,
    KeepOnline,
    DualSim,
    Security,
    Troubleshooting,
}

@Composable
fun HelpScreen(
    onOpenTopic: (HelpTopic) -> Unit,
    onBack: () -> Unit,
) {
    Surface(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = stringResource(R.string.help_title),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = stringResource(R.string.help_intro),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f),
            )
            HelpTopic.entries.forEach { topic ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onOpenTopic(topic) },
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = stringResource(topicTitle(topic)),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Text(
                            text = stringResource(topicBlurb(topic)),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                        )
                    }
                }
            }
            Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.action_back))
            }
        }
    }
}

@Composable
fun HelpTopicScreen(
    topic: HelpTopic,
    onBack: () -> Unit,
) {
    Surface(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = stringResource(topicTitle(topic)),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = stringResource(topicBody(topic)),
                style = MaterialTheme.typography.bodyMedium,
            )
            Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.action_back))
            }
        }
    }
}

private fun topicTitle(topic: HelpTopic): Int = when (topic) {
    HelpTopic.GettingStarted -> R.string.help_started_title
    HelpTopic.KeepOnline -> R.string.help_online_title
    HelpTopic.DualSim -> R.string.help_dualsim_title
    HelpTopic.Security -> R.string.help_security_title
    HelpTopic.Troubleshooting -> R.string.help_trouble_title
}

private fun topicBlurb(topic: HelpTopic): Int = when (topic) {
    HelpTopic.GettingStarted -> R.string.help_started_blurb
    HelpTopic.KeepOnline -> R.string.help_online_blurb
    HelpTopic.DualSim -> R.string.help_dualsim_blurb
    HelpTopic.Security -> R.string.help_security_blurb
    HelpTopic.Troubleshooting -> R.string.help_trouble_blurb
}

private fun topicBody(topic: HelpTopic): Int = when (topic) {
    HelpTopic.GettingStarted -> R.string.help_started_body
    HelpTopic.KeepOnline -> R.string.help_online_body
    HelpTopic.DualSim -> R.string.help_dualsim_body
    HelpTopic.Security -> R.string.help_security_body
    HelpTopic.Troubleshooting -> R.string.help_trouble_body
}
