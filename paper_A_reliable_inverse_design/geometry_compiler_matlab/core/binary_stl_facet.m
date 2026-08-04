function [normal, triangle] = binary_stl_facet( ...
        vertices, face, errorId)
%BINARY_STL_FACET Convert one indexed face to its exact float32 STL record.

    triangle = single(vertices(face, :));
    normalDouble = cross( ...
        double(triangle(2, :) - triangle(1, :)), ...
        double(triangle(3, :) - triangle(1, :)));
    normalNorm = norm(normalDouble);
    if ~isfinite(normalNorm) || normalNorm == 0
        throw(MException(errorId, ...
            'cannot serialize a degenerate STL triangle'));
    end
    normal = single(normalDouble ./ normalNorm);
end
