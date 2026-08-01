#pragma once
#include "DataSender.h"
#include "SourceFactory.h"
#include "StreamOptions.h"

// Runs the fixed-rate polling loop: pulls points from `source`, batches them into `sender`, and sends whenever the batch fills.
//
// Exits when any of the following happens:
// - opts.limit > 0 and that many points have been sent
// - a batch fails to send (remaining unsent points are dumped to disk)
// - the process receives SIGINT or SIGTERM (any buffered points below
//   batch_size are flushed as a final partial batch before returning)
//
// Returns the process exit code.
int run_polling_loop(DataSender& sender, DataSource& source, const StreamOptions& opts);