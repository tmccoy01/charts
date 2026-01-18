# Perl Dependencies for FAA Chart Processing
requires 'perl', '5.30.0';

# Core Dependencies
requires 'Geo::GDAL', '3.0';
requires 'Geo::OSR', '3.0';
requires 'Geo::OGR', '3.0';

# Parallel processing
requires 'Parallel::ForkManager', '2.02';

# System utilities
requires 'File::Find', '1.00';
requires 'File::Path', '2.00';
requires 'File::Copy', '2.00';
requires 'IPC::Open3', '1.00';
requires 'Symbol', '1.00';

# Date handling
requires 'Time::Piece', '1.00';
requires 'DateTime', '1.00';

# JSON handling
requires 'JSON', '4.00';

on 'test' => requires 'Test::More', '1.00'
