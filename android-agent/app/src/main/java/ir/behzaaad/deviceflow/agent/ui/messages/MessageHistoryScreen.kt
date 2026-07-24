package ir.behzaaad.deviceflow.agent.ui.messages

import android.app.DatePickerDialog
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import ir.behzaaad.deviceflow.agent.R
import ir.behzaaad.deviceflow.agent.data.AgentPreferences
import ir.behzaaad.deviceflow.agent.data.LocalMessage
import java.text.DateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

private enum class DirectionFilter { All, Out, In }
private enum class StatusFilter { All, Sent, Failed, Received }

@Composable
fun MessageHistoryScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val prefs = remember { AgentPreferences(context) }
    val lifecycleOwner = LocalLifecycleOwner.current

    var all by remember { mutableStateOf(prefs.allMessages()) }
    var query by remember { mutableStateOf("") }
    var direction by remember { mutableStateOf(DirectionFilter.All) }
    var status by remember { mutableStateOf(StatusFilter.All) }
    var fromDayStartMs by remember { mutableLongStateOf(0L) }
    var toDayEndMs by remember { mutableLongStateOf(0L) }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                all = prefs.allMessages()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    val filtered = remember(all, query, direction, status, fromDayStartMs, toDayEndMs) {
        all.filter { msg ->
            val dirOk = when (direction) {
                DirectionFilter.All -> true
                DirectionFilter.Out -> msg.direction == "out"
                DirectionFilter.In -> msg.direction == "in"
            }
            val statusOk = when (status) {
                StatusFilter.All -> true
                StatusFilter.Sent -> msg.status == "sent"
                StatusFilter.Failed -> msg.status == "failed"
                StatusFilter.Received -> msg.status == "received"
            }
            val dateOk =
                (fromDayStartMs == 0L || msg.atMs >= fromDayStartMs) &&
                    (toDayEndMs == 0L || msg.atMs <= toDayEndMs)
            val q = query.trim().lowercase(Locale.getDefault())
            val queryOk =
                q.isEmpty() ||
                    msg.peer.lowercase(Locale.getDefault()).contains(q) ||
                    msg.body.lowercase(Locale.getDefault()).contains(q) ||
                    msg.status.lowercase(Locale.getDefault()).contains(q)
            dirOk && statusOk && dateOk && queryOk
        }
    }

    val dateFmt = remember {
        DateFormat.getDateInstance(DateFormat.MEDIUM)
    }
    val dateTimeFmt = remember {
        DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT)
    }

    Surface(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = stringResource(R.string.messages_title),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = stringResource(R.string.messages_subtitle, filtered.size, all.size),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            )

            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text(stringResource(R.string.messages_search)) },
            )

            Text(
                text = stringResource(R.string.messages_filter_direction),
                style = MaterialTheme.typography.labelLarge,
            )
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                FilterChip(
                    selected = direction == DirectionFilter.All,
                    onClick = { direction = DirectionFilter.All },
                    label = { Text(stringResource(R.string.messages_filter_all)) },
                )
                FilterChip(
                    selected = direction == DirectionFilter.Out,
                    onClick = { direction = DirectionFilter.Out },
                    label = { Text(stringResource(R.string.msg_out)) },
                )
                FilterChip(
                    selected = direction == DirectionFilter.In,
                    onClick = { direction = DirectionFilter.In },
                    label = { Text(stringResource(R.string.msg_in)) },
                )
            }

            Text(
                text = stringResource(R.string.messages_filter_status),
                style = MaterialTheme.typography.labelLarge,
            )
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                FilterChip(
                    selected = status == StatusFilter.All,
                    onClick = { status = StatusFilter.All },
                    label = { Text(stringResource(R.string.messages_filter_all)) },
                )
                FilterChip(
                    selected = status == StatusFilter.Sent,
                    onClick = { status = StatusFilter.Sent },
                    label = { Text(stringResource(R.string.messages_status_sent)) },
                )
                FilterChip(
                    selected = status == StatusFilter.Failed,
                    onClick = { status = StatusFilter.Failed },
                    label = { Text(stringResource(R.string.messages_status_failed)) },
                )
                FilterChip(
                    selected = status == StatusFilter.Received,
                    onClick = { status = StatusFilter.Received },
                    label = { Text(stringResource(R.string.messages_status_received)) },
                )
            }

            Text(
                text = stringResource(R.string.messages_filter_date),
                style = MaterialTheme.typography.labelLarge,
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedButton(
                    onClick = {
                        pickDate(context, fromDayStartMs) { start ->
                            fromDayStartMs = startOfDay(start)
                        }
                    },
                    modifier = Modifier.weight(1f),
                ) {
                    Text(
                        if (fromDayStartMs == 0L) {
                            stringResource(R.string.messages_from_date)
                        } else {
                            stringResource(
                                R.string.messages_from_date_value,
                                dateFmt.format(Date(fromDayStartMs)),
                            )
                        },
                    )
                }
                OutlinedButton(
                    onClick = {
                        pickDate(context, toDayEndMs) { end ->
                            toDayEndMs = endOfDay(end)
                        }
                    },
                    modifier = Modifier.weight(1f),
                ) {
                    Text(
                        if (toDayEndMs == 0L) {
                            stringResource(R.string.messages_to_date)
                        } else {
                            stringResource(
                                R.string.messages_to_date_value,
                                dateFmt.format(Date(toDayEndMs)),
                            )
                        },
                    )
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(
                    onClick = {
                        query = ""
                        direction = DirectionFilter.All
                        status = StatusFilter.All
                        fromDayStartMs = 0L
                        toDayEndMs = 0L
                    },
                    modifier = Modifier.weight(1f),
                ) {
                    Text(stringResource(R.string.messages_clear_filters))
                }
                OutlinedButton(
                    onClick = {
                        prefs.clearMessageHistory()
                        all = emptyList()
                    },
                    modifier = Modifier.weight(1f),
                ) {
                    Text(stringResource(R.string.messages_clear_history))
                }
            }

            Column(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (filtered.isEmpty()) {
                    Text(
                        text = stringResource(R.string.messages_empty),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f),
                    )
                } else {
                    filtered.forEach { msg ->
                        MessageCard(msg, dateTimeFmt)
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))
            }

            Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.action_back))
            }
        }
    }
}

@Composable
private fun MessageCard(message: LocalMessage, dateTimeFmt: DateFormat) {
    val dir = if (message.direction == "in") {
        stringResource(R.string.msg_in)
    } else {
        stringResource(R.string.msg_out)
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = "$dir · ${message.peer}",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = message.status,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            Text(
                text = dateTimeFmt.format(Date(message.atMs)),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            )
            Text(
                text = message.body.ifBlank { "—" },
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

private fun pickDate(
    context: android.content.Context,
    initialMs: Long,
    onPicked: (Long) -> Unit,
) {
    val cal = Calendar.getInstance()
    if (initialMs > 0L) cal.timeInMillis = initialMs
    DatePickerDialog(
        context,
        { _, year, month, day ->
            val picked = Calendar.getInstance().apply {
                set(Calendar.YEAR, year)
                set(Calendar.MONTH, month)
                set(Calendar.DAY_OF_MONTH, day)
            }
            onPicked(picked.timeInMillis)
        },
        cal.get(Calendar.YEAR),
        cal.get(Calendar.MONTH),
        cal.get(Calendar.DAY_OF_MONTH),
    ).show()
}

private fun startOfDay(ms: Long): Long {
    return Calendar.getInstance().apply {
        timeInMillis = ms
        set(Calendar.HOUR_OF_DAY, 0)
        set(Calendar.MINUTE, 0)
        set(Calendar.SECOND, 0)
        set(Calendar.MILLISECOND, 0)
    }.timeInMillis
}

private fun endOfDay(ms: Long): Long {
    return Calendar.getInstance().apply {
        timeInMillis = ms
        set(Calendar.HOUR_OF_DAY, 23)
        set(Calendar.MINUTE, 59)
        set(Calendar.SECOND, 59)
        set(Calendar.MILLISECOND, 999)
    }.timeInMillis
}
