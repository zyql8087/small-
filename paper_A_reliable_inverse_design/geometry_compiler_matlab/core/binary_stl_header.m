function header = binary_stl_header()
%BINARY_STL_HEADER Return the fixed 80-byte M03 binary STL header.

    header = zeros(1, 80, 'uint8');
    label = uint8('MATLABGyroid continuous CSG STL');
    header(1:numel(label)) = label;
end
