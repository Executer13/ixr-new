# ring_buffer.py - Optimized circular buffer for high-performance streaming data

import numpy as np


class RingBuffer:
    """
    High-performance circular buffer using pre-allocated numpy arrays.
    Zero-copy operations and efficient memory management for real-time streaming.
    """

    def __init__(self, capacity, dtype=np.float64):
        """
        Initialize ring buffer with fixed capacity.

        Args:
            capacity: Maximum number of elements to store
            dtype: Data type for the buffer (default: float64)
        """
        self.capacity = capacity
        self.dtype = dtype
        self.buffer = np.zeros(capacity, dtype=dtype)
        self.write_idx = 0
        self.size = 0  # Current number of elements

    def extend(self, data):
        """
        Append multiple elements efficiently (batch operation).

        Args:
            data: Array-like data to append
        """
        data = np.asarray(data, dtype=self.dtype)
        n = len(data)

        if n >= self.capacity:
            # If data is larger than capacity, only keep the most recent elements
            self.buffer[:] = data[-self.capacity:]
            self.write_idx = 0
            self.size = self.capacity
            return

        # Calculate how many elements fit before wrapping
        space_to_end = self.capacity - self.write_idx

        if n <= space_to_end:
            # Data fits without wrapping
            self.buffer[self.write_idx:self.write_idx + n] = data
            self.write_idx = (self.write_idx + n) % self.capacity
        else:
            # Data wraps around
            self.buffer[self.write_idx:] = data[:space_to_end]
            remainder = n - space_to_end
            self.buffer[:remainder] = data[space_to_end:]
            self.write_idx = remainder

        self.size = min(self.size + n, self.capacity)

    def get_data(self, max_items=None):
        """
        Get data as contiguous numpy array (zero-copy view when possible).

        Args:
            max_items: Maximum number of most recent items to return (None = all)

        Returns:
            Numpy array view of the data in chronological order
        """
        if self.size == 0:
            return np.array([], dtype=self.dtype)

        if max_items is None:
            max_items = self.size
        else:
            max_items = min(max_items, self.size)

        if self.size < self.capacity:
            # Buffer not yet full, data is contiguous from start
            return self.buffer[:self.size][-max_items:]
        else:
            # Buffer is full, need to unwrap
            # Data starts at write_idx (oldest) and wraps around
            result = np.empty(max_items, dtype=self.dtype)
            start_idx = (self.write_idx - max_items) % self.capacity

            if start_idx + max_items <= self.capacity:
                # Data is contiguous
                return self.buffer[start_idx:start_idx + max_items]
            else:
                # Data wraps around
                first_chunk = self.capacity - start_idx
                result[:first_chunk] = self.buffer[start_idx:]
                result[first_chunk:] = self.buffer[:max_items - first_chunk]
                return result

    def get_recent(self, n_samples):
        """
        Get the N most recent samples efficiently.

        Args:
            n_samples: Number of recent samples to retrieve

        Returns:
            Numpy array of the most recent n_samples
        """
        return self.get_data(max_items=n_samples)

    def clear(self):
        """Clear the buffer."""
        self.write_idx = 0
        self.size = 0
        # Don't reallocate, just reset indices (reuse memory)

    def __len__(self):
        """Return current number of elements in buffer."""
        return self.size

    def is_full(self):
        """Check if buffer is at capacity."""
        return self.size == self.capacity


class TwoBufferRing:
    """
    Dual ring buffer for synchronized time and value data.
    Optimized for streaming sensor data where timestamps and values are paired.
    """

    def __init__(self, capacity, dtype=np.float64):
        """
        Initialize dual ring buffers.

        Args:
            capacity: Maximum number of samples
            dtype: Data type for value buffer (timestamps always float64)
        """
        self.time_buffer = RingBuffer(capacity, dtype=np.float64)
        self.value_buffer = RingBuffer(capacity, dtype=dtype)

    def extend(self, timestamps, values):
        """
        Append synchronized timestamp-value pairs.

        Args:
            timestamps: Array of timestamps
            values: Array of corresponding values
        """
        self.time_buffer.extend(timestamps)
        self.value_buffer.extend(values)

    def get_data(self, max_items=None, skip_initial=0):
        """
        Get synchronized time and value data.

        Args:
            max_items: Maximum number of items (None = all available)
            skip_initial: Skip first N samples (for buffering warm-up)

        Returns:
            Tuple of (times, values) as numpy arrays
        """
        if skip_initial >= len(self.time_buffer):
            return np.array([]), np.array([])

        times = self.time_buffer.get_data(max_items)
        values = self.value_buffer.get_data(max_items)

        if skip_initial > 0:
            times = times[skip_initial:]
            values = values[skip_initial:]

        return times, values

    def __len__(self):
        """Return current number of samples."""
        return len(self.time_buffer)

    def clear(self):
        """Clear both buffers."""
        self.time_buffer.clear()
        self.value_buffer.clear()
