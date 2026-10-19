The file /app/corpus.txt contains plain ASCII text.

Define a "word" as follows:

- Split the text into tokens on whitespace.
- Strip leading and trailing punctuation characters from each token. The
  punctuation set is exactly these 12 characters: . , ; : ! ? " ' ( ) -
  Strip repeatedly until both ends are not punctuation. Internal punctuation
  is kept (e.g. `state-of-the-art` is one single word).
- If the resulting token is empty, skip it.
- If the resulting token contains any digit (0-9), skip it.
- Word matching is case-insensitive: normalize every word to lowercase.

Create the file /app/report.txt with exactly this content:

- Line 1: the total number of word tokens remaining after the rules above,
  as a decimal integer.
- Line 2: the number of distinct words (case-insensitive), as a decimal
  integer.
- Lines 3-7: the 5 most frequent words, one per line, each line in the
  format `<word> <count>` (word and count separated by exactly one space).
  Rank by count descending; when two words have the same count, the word
  that is smaller in ASCII order ranks first.

Rules for the whole file:

- The file must end with a trailing newline.
- No other lines, spaces, or blank lines are allowed.
- Integers must be written in decimal without leading zeros.
